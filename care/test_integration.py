from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class ProjectIntegrationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "integration", password="testing-only-9384"
        )

    def test_login_form_preserves_return_path(self):
        response = self.client.get("/login/?next=/plant-care/")
        self.assertContains(response, 'name="next" value="/plant-care/"')

    def test_existing_auth_returns_to_care(self):
        response = self.client.post(
            "/login/",
            {
                "username": "integration",
                "password": "testing-only-9384",
                "next": "/plant-care/",
            },
        )
        self.assertRedirects(response, "/plant-care/")
        page = self.client.get("/plant-care/")
        self.assertContains(page, "Your plants will appear here")
        self.assertNotContains(page, "css/style.css")
        self.assertContains(self.client.get("/"), 'href="/plant-care/"')

    def test_external_redirect_is_rejected(self):
        response = self.client.post(
            "/login/",
            {
                "username": "integration",
                "password": "testing-only-9384",
                "next": "https://example.org/",
            },
        )
        self.assertRedirects(response, reverse("show_main"))

    def test_home_redirect_uses_group_landing(self):
        self.assertRedirects(
            self.client.get(reverse("care:landing")), reverse("show_main")
        )

