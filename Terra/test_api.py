"""Run with python manage.py test Terra.test_api"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from my_plants.models import Plant


class MobileApiSmokeTests(TestCase):
    def setUp(self):
        self.alice = get_user_model().objects.create_user(username="alice_mobile", password="StrongPassword123!")
        self.bob = get_user_model().objects.create_user(username="bob_mobile", password="StrongPassword123!")
        self.client = APIClient()

    def test_all_five_routes_reject_anonymous_users(self):
        for path in ("spaces", "plans", "my-plants", "care-tasks", "journal-entries"):
            with self.subTest(path=path):
                resp = self.client.get(f"/api/v1/{path}/")
                self.assertIn(resp.status_code, (401, 403))

    def test_all_five_routes_return_lists_for_authenticated_user(self):
        self.client.force_authenticate(user=self.alice)
        for path in ("spaces", "plans", "my-plants", "care-tasks", "journal-entries"):
            with self.subTest(path=path):
                resp = self.client.get(f"/api/v1/{path}/")
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.json(), [])

    def test_my_plants_are_user_scoped(self):
        other = Plant.objects.create(owner=self.bob, name="Private basil", species_name="Ocimum basilicum")
        self.client.force_authenticate(user=self.alice)
        self.assertEqual(self.client.get(f"/api/v1/my-plants/{other.pk}/").status_code, 404)

    def test_care_task_cannot_reference_someone_elses_plant(self):
        other = Plant.objects.create(owner=self.bob, name="Bob's basil", species_name="Ocimum basilicum")
        self.client.force_authenticate(user=self.alice)
        resp = self.client.post("/api/v1/care-tasks/", {
            "plant": other.pk, "title": "Water basil", "action_type": "Watering", "due_date": "2026-11-21"
        }, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_journal_cannot_reference_someone_elses_plant(self):
        other = Plant.objects.create(owner=self.bob, name="Bob's basil", species_name="Ocimum basilicum")
        self.client.force_authenticate(user=self.alice)
        resp = self.client.post("/api/v1/journal-entries/", {
            "plant": other.pk, "entry_date": "2026-11-19", "entry_type": "growth", "title": "secret", "notes": "private"
        }, format="json")
        self.assertEqual(resp.status_code, 400)
