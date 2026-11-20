"""My Plants REST API tests. Run: python manage.py test my_plants.test_api"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from main.models import GardenJournalEntry
from .models import Plant

LIST_URL = "/api/v1/my-plants/"


def detail_url(pk):
    return f"{LIST_URL}{pk}/"


class MyPlantsApiTests(TestCase):
    def setUp(self):
        cache.clear()  # reset rate-limit counters between tests
        User = get_user_model()
        self.farel = User.objects.create_user(username="farel_api", password="StrongPassword123!")
        self.other = User.objects.create_user(username="other_api", password="StrongPassword123!")
        self.client = APIClient()
        self.client.force_authenticate(user=self.farel)

        today = timezone.localdate()
        self.basil = Plant.objects.create(
            owner=self.farel, name="Basil", species_name="Ocimum basilicum",
            planted_on=today - timedelta(days=10),
        )
        self.chili = Plant.objects.create(
            owner=self.farel, name="Chili", species_name="Capsicum annuum",
            planted_on=today - timedelta(days=40), growth_stage=Plant.Stage.FLOWERING,
        )
        self.tomato = Plant.objects.create(
            owner=self.farel, name="Tomato", species_name="Solanum lycopersicum",
            planted_on=today - timedelta(days=90), growth_stage=Plant.Stage.FINISHED,
        )
        self.foreign = Plant.objects.create(
            owner=self.other, name="Other mint", species_name="Mentha",
        )

    def names(self, response):
        return [item["name"] for item in response.json()]

    # --- authentication -------------------------------------------------

    def test_guest_gets_401_json(self):
        response = APIClient().get(LIST_URL)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["status_code"], 401)
        self.assertIn("detail", response.json())

    def test_token_login_then_list(self):
        client = APIClient()
        login = client.post(
            "/api/v1/auth/token/",
            {"username": "farel_api", "password": "StrongPassword123!"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        client.credentials(HTTP_AUTHORIZATION=f"Token {login.json()['token']}")
        response = client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(self.names(response), ["Basil", "Chili", "Tomato"])

    def test_wrong_password_is_rejected(self):
        response = APIClient().post(
            "/api/v1/auth/token/", {"username": "farel_api", "password": "wrong"}, format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("non_field_errors", response.json())

    # --- read -----------------------------------------------------------

    def test_list_only_contains_own_plants_with_computed_fields(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Other mint", self.names(response))
        basil = next(p for p in response.json() if p["name"] == "Basil")
        self.assertEqual(basil["status"], "active")
        self.assertEqual(basil["days_growing"], 10)
        self.assertEqual(basil["growth_stage"], "growing")

    def test_detail_of_another_users_plant_is_404(self):
        response = self.client.get(detail_url(self.foreign.pk))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["status_code"], 404)

    def test_search_matches_name_or_species(self):
        self.assertEqual(self.names(self.client.get(LIST_URL, {"search": "bas"})), ["Basil"])
        self.assertEqual(self.names(self.client.get(LIST_URL, {"search": "capsicum"})), ["Chili"])
        self.assertEqual(self.names(self.client.get(LIST_URL, {"search": "mint"})), [])

    def test_filter_by_status_and_stage(self):
        active = self.names(self.client.get(LIST_URL, {"status": "active"}))
        self.assertCountEqual(active, ["Basil", "Chili"])
        finished = self.names(self.client.get(LIST_URL, {"status": "finished"}))
        self.assertEqual(finished, ["Tomato"])
        flowering = self.names(self.client.get(LIST_URL, {"stage": "flowering"}))
        self.assertEqual(flowering, ["Chili"])

    def test_ordering(self):
        self.assertEqual(
            self.names(self.client.get(LIST_URL, {"ordering": "name"})), ["Basil", "Chili", "Tomato"],
        )
        self.assertEqual(
            self.names(self.client.get(LIST_URL, {"ordering": "planted_on"})), ["Tomato", "Chili", "Basil"],
        )

    def test_unknown_filter_values_are_ignored(self):
        response = self.client.get(LIST_URL, {"status": "nope", "stage": "nope", "ordering": "owner"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 3)

    # --- create / update / delete --------------------------------------

    def test_create_sets_owner_and_ignores_read_only_fields(self):
        response = self.client.post(
            LIST_URL,
            {"name": "Mint", "species_name": "Mentha spicata", "growth_stage": "finished",
             "planted_on": str(timezone.localdate())},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        plant = Plant.objects.get(pk=response.json()["id"])
        self.assertEqual(plant.owner, self.farel)
        self.assertEqual(plant.growth_stage, Plant.Stage.GROWING)

    def test_create_validation_errors_are_per_field(self):
        tomorrow = timezone.localdate() + timedelta(days=1)
        response = self.client.post(
            LIST_URL, {"name": "   ", "species_name": "", "planted_on": str(tomorrow)}, format="json",
        )
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["status_code"], 400)
        self.assertIn("name", body)
        self.assertIn("species_name", body)
        self.assertEqual(body["planted_on"], ["Planting date cannot be in the future."])

    def test_partial_update_cannot_change_growth_stage(self):
        response = self.client.patch(
            detail_url(self.basil.pk), {"notes": "Watered", "growth_stage": "finished"}, format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.basil.refresh_from_db()
        self.assertEqual(self.basil.notes, "Watered")
        self.assertEqual(self.basil.growth_stage, Plant.Stage.GROWING)

    def test_cannot_update_or_delete_another_users_plant(self):
        self.assertEqual(
            self.client.patch(detail_url(self.foreign.pk), {"name": "x"}, format="json").status_code, 404,
        )
        self.assertEqual(self.client.delete(detail_url(self.foreign.pk)).status_code, 404)
        self.assertTrue(Plant.objects.filter(pk=self.foreign.pk).exists())

    def test_delete_own_plant(self):
        response = self.client.delete(detail_url(self.basil.pk))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Plant.objects.filter(pk=self.basil.pk).exists())

    def test_delete_plant_used_by_journal_returns_409(self):
        GardenJournalEntry.objects.create(
            user=self.farel, plant=self.chili, plant_name=self.chili.name,
            entry_date=timezone.localdate(), entry_type="growth", title="New leaves",
        )
        response = self.client.delete(detail_url(self.chili.pk))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["status_code"], 409)
        self.assertTrue(Plant.objects.filter(pk=self.chili.pk).exists())
