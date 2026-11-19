"""Garden Setup DRF tests, run: python manage.py test garden_setup.test_api."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import GrowingSpace


class GardenSetupApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.sean = User.objects.create_user(
            username="sean_api_test", password="StrongPassword123!"
        )
        self.other_user = User.objects.create_user(
            username="other_api_test", password="StrongPassword123!"
        )
        self.client = APIClient()
        self.payload = {
            "name": "Balcony Jakarta",
            "environment": "outdoor",
            "space_type": "balcony",
            "geocoding_id": 1642911,
            "city": "Jakarta",
            "region": "DKI Jakarta",
            "country": "Indonesia",
            "latitude": "-6.200000",
            "longitude": "106.816666",
            "timezone": "Asia/Jakarta",
            "sunlight_range": "4-6",
            "light_exposure": "direct",
            "growing_medium": "soil",
            "rain_access": "exposed",
            "support_available": "yes",
            "pot_capacity": 3,
            "care_availability": "daily",
            "notes": "Testing REST API",
        }

    def test_guest_cannot_access_list(self):
        response = self.client.get("/api/v1/spaces/")
        self.assertIn(response.status_code, (401, 403))

    def test_create_list_update_delete(self):
        self.client.force_authenticate(user=self.sean)
        created = self.client.post("/api/v1/spaces/", self.payload, format="json")
        self.assertEqual(created.status_code, 201, created.content)
        pk = created.data["id"]
        self.assertEqual(GrowingSpace.objects.get(pk=pk).user, self.sean)

        listed = self.client.get("/api/v1/spaces/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data), 1)

        updated = self.client.patch(
            f"/api/v1/spaces/{pk}/", {"name": "New Balcony"}, format="json"
        )
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(GrowingSpace.objects.get(pk=pk).name, "New Balcony")

        deleted = self.client.delete(f"/api/v1/spaces/{pk}/")
        self.assertEqual(deleted.status_code, 204, deleted.content)
        self.assertFalse(GrowingSpace.objects.filter(pk=pk).exists())

    def test_cannot_read_or_edit_another_users_space(self):
        other_space = GrowingSpace.objects.create(user=self.other_user, **self.payload)
        self.client.force_authenticate(user=self.sean)

        self.assertEqual(self.client.get("/api/v1/spaces/").data, [])
        self.assertEqual(
            self.client.get(f"/api/v1/spaces/{other_space.pk}/").status_code,
            404,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/spaces/{other_space.pk}/",
                {"name": "Not allowed"},
                format="json",
            ).status_code,
            404,
        )

    def test_indoor_cannot_have_exposed_rain(self):
        self.client.force_authenticate(user=self.sean)
        invalid = {**self.payload, "environment": "indoor", "rain_access": "exposed"}
        response = self.client.post("/api/v1/spaces/", invalid, format="json")
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("rain_access", response.data)

    def test_other_type_requires_description(self):
        self.client.force_authenticate(user=self.sean)
        invalid = {**self.payload, "space_type": "other", "other_space_type": ""}
        response = self.client.post("/api/v1/spaces/", invalid, format="json")
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("other_space_type", response.data)
