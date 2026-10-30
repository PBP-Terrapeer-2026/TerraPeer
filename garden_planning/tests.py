import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .forms import PotForm
from .models import Plan, PlanPlant, Plant, Pot


class PotFormTests(TestCase):
    def test_accepts_valid_pot_data(self):
        form = PotForm({
            "name": "Pot Terakota",
            "size_cm": 25,
            "material": "terakota",
        })

        self.assertTrue(form.is_valid(), form.errors)

    def test_rejects_material_outside_available_choices(self):
        form = PotForm({
            "name": "Pot Aneh",
            "size_cm": 25,
            "material": "bambu",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("material", form.errors)

    def test_removes_html_and_script_content_from_pot_name(self):
        form = PotForm({
            "name": "<script>alert('xss')</script><b>Pot Aman</b>",
            "size_cm": 25,
            "material": "terakota",
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["name"], "Pot Aman")

    def test_rejects_name_that_contains_only_active_content(self):
        form = PotForm({
            "name": "<script>alert('xss')</script>",
            "size_cm": 25,
            "material": "terakota",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)


class RecommendPlantsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="gardener",
            password="test-password",
        )
        self.client.force_login(self.user)
        self.url = reverse("garden_planning:recommend_plants")

    def test_invalid_json_returns_bad_request(self):
        response = self.client.post(
            self.url,
            data="{not valid json",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    @patch("garden_planning.views.fetch_plants_from_perenual")
    def test_recommendation_maps_api_plant_data_into_response(self, fetch_plants):
        fetch_plants.side_effect = [
            [{
                "id": 12345,
                "common_name": "Basil",
                "watering": "average",
                "sunlight": ["full sun"],
                "description": "A culinary herb. It attracts pollinators.",
                "default_image": {"medium_url": "https://example.com/basil.jpg"},
            }],
            [],
            [],
        ]

        response = self.client.post(
            self.url,
            data=json.dumps({
                "avg_rain_mm": 2,
                "avg_temp_c": 25,
                "avg_radiation": 18,
                "avg_humidity": 60,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        plant_data = response.json()["plants"][0]
        self.assertEqual(plant_data["name"], "Basil")
        self.assertEqual(plant_data["watering"], "average")
        self.assertEqual(plant_data["sunlight"], ["full sun"])
        self.assertEqual(plant_data["description"], "A culinary herb.")
        self.assertEqual(plant_data["image_url"], "https://example.com/basil.jpg")
        self.assertTrue(Plant.objects.filter(perenual_id=12345, name="Basil").exists())
        self.assertEqual(fetch_plants.call_count, 3)


class GardenPlanningApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="api-gardener",
            password="test-password",
        )
        self.client.force_login(self.user)

    def test_pot_api_creates_pot_for_current_user(self):
        response = self.client.post(
            reverse("garden_planning:pot_list_create"),
            data=json.dumps({"name": "Pot Terakota", "size_cm": 25, "material": "terakota"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        pot = Pot.objects.get(pk=response.json()["id"])
        self.assertEqual(pot.owner, self.user)
        self.assertEqual(pot.name, "Pot Terakota")

    def test_pot_api_rejects_unsupported_material(self):
        response = self.client.post(
            reverse("garden_planning:pot_list_create"),
            data=json.dumps({"name": "Pot", "size_cm": 25, "material": "bambu"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Pot.objects.count(), 0)

    def test_adding_plant_rejects_different_recommendation_location(self):
        plan = Plan.objects.create(
            owner=self.user,
            name="Kebun rumah",
            latitude=-6.2,
            longitude=106.8,
        )
        plant = Plant.objects.create(name="Kemangi")

        response = self.client.post(
            reverse("garden_planning:planplant_list_create", kwargs={"plan_pk": plan.pk}),
            data=json.dumps({
                "plant_id": plant.pk,
                "recommendation_latitude": -7.25,
                "recommendation_longitude": 112.75,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(PlanPlant.objects.count(), 0)

    def test_adding_plant_accepts_matching_recommendation_location(self):
        plan = Plan.objects.create(
            owner=self.user,
            name="Kebun rumah",
            latitude=-6.2,
            longitude=106.8,
        )
        plant = Plant.objects.create(name="Kemangi")

        response = self.client.post(
            reverse("garden_planning:planplant_list_create", kwargs={"plan_pk": plan.pk}),
            data=json.dumps({
                "plant_id": plant.pk,
                "recommendation_latitude": -6.2,
                "recommendation_longitude": 106.8,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(PlanPlant.objects.filter(plan=plan, plant=plant).exists())
