"""Cross-module API behaviour: docs, error format, CORS and rate limiting.

Run: python manage.py test Terra.test_api_platform
"""
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from my_plants.api import MyPlantViewSet


class ApiPlatformTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(username="platform", password="StrongPassword123!")
        self.client = APIClient()

    # --- documentation ---------------------------------------------------

    def test_openapi_schema_is_public_and_lists_every_module(self):
        response = self.client.get("/api/v1/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json")
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        for path in ("spaces", "plans", "my-plants", "care-tasks", "journal-entries"):
            self.assertIn(f"/api/v1/{path}/", paths)
        self.assertIn("/api/v1/auth/token/", paths)

    def test_swagger_and_redoc_pages_load(self):
        self.assertEqual(self.client.get("/api/v1/docs/").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/redoc/").status_code, 200)

    # --- error format ----------------------------------------------------

    def test_unknown_api_path_returns_json_404(self):
        response = self.client.get("/api/v1/does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.json(), {"detail": "Not found.", "status_code": 404})

    def test_missing_trailing_slash_still_redirects(self):
        response = self.client.get("/api/v1/my-plants")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "/api/v1/my-plants/")

    def test_unexpected_exception_returns_json_500_without_traceback(self):
        self.client.force_authenticate(user=self.user)
        with mock.patch.object(MyPlantViewSet, "get_queryset", side_effect=RuntimeError("boom")), \
                self.assertLogs("terrapeer.api", level="ERROR"):
            response = self.client.get("/api/v1/my-plants/")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Internal server error.", "status_code": 500})
        self.assertNotIn("boom", response.content.decode())

    def test_web_pages_keep_their_html_404(self):
        response = self.client.get("/my-plants/999999/")
        self.assertNotEqual(response.get("Content-Type"), "application/json")

    # --- CORS --------------------------------------------------------------

    def test_cors_header_only_on_api(self):
        origin = {"HTTP_ORIGIN": "http://localhost:5000"}
        api = self.client.get("/api/v1/schema/", **origin)
        self.assertEqual(api["Access-Control-Allow-Origin"], "*")
        web = self.client.get("/", **origin)
        self.assertNotIn("Access-Control-Allow-Origin", web)

    def test_cors_preflight_for_token_login(self):
        response = self.client.options(
            "/api/v1/auth/token/",
            HTTP_ORIGIN="http://localhost:5000",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("authorization", response["Access-Control-Allow-Headers"].lower())

    # --- rate limiting -----------------------------------------------------

    def test_login_is_limited_to_10_attempts_per_minute(self):
        body = {"username": "platform", "password": "wrong"}
        for _ in range(10):
            self.assertEqual(self.client.post("/api/v1/auth/token/", body, format="json").status_code, 400)
        response = self.client.post("/api/v1/auth/token/", body, format="json")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["status_code"], 429)
        self.assertIn("Retry-After", response)
