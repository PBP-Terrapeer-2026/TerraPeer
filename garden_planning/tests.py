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

    @patch("garden_planning.views.fetch_plants_from_perenual")
    def test_recommendation_cleans_premium_text_and_truncates_long_fields(self, fetch_plants):
        Plant.objects.create(
            perenual_id=23456,
            name="Old cached name",
            watering="Old value",
        )
        Plant.objects.create(
            perenual_id=23457,
            name="Cached premium plant",
            watering="Upgrade Plans To Premium",
        )
        fetch_plants.side_effect = [[
            {
                "id": 23456,
                "common_name": "Long name " * 25,
                "scientific_name": [],
                "watering": "frequent " * 10,
                "sunlight": ["full sun"],
                "description": "A plant description.",
            },
            {
                "id": 23457,
                "common_name": "Premium plant",
                "scientific_name": [],
                "watering": "Upgrade Plans To Premium to see this data",
                "sunlight": ["part sun"],
                "description": "Another plant description.",
            },
        ], [], []]

        response = self.client.post(
            self.url,
            data=json.dumps({"avg_rain_mm": 2, "avg_radiation": 18}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        plants = response.json()["plants"]
        plant = Plant.objects.get(perenual_id=23456)
        premium_plant = Plant.objects.get(perenual_id=23457)
        self.assertLessEqual(len(plant.name), Plant._meta.get_field("name").max_length)
        self.assertLessEqual(len(plant.watering), Plant._meta.get_field("watering").max_length)
        self.assertEqual(len(plant.watering), Plant._meta.get_field("watering").max_length)
        self.assertEqual(premium_plant.watering, "")
        self.assertIn(premium_plant.name, [item["name"] for item in plants])

    @patch("garden_planning.views.fetch_plants_from_perenual")
    def test_recommendation_uses_id_when_plant_has_no_names(self, fetch_plants):
        fetch_plants.side_effect = [[{
            "id": 34567,
            "common_name": "",
            "scientific_name": [],
            "watering": "average",
            "sunlight": ["part sun"],
            "description": "A plant description.",
        }], [], []]

        response = self.client.post(
            self.url,
            data=json.dumps({"avg_rain_mm": 2, "avg_radiation": 18}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["plants"][0]["name"], "Plant #34567")
        self.assertTrue(Plant.objects.filter(perenual_id=34567, name="Plant #34567").exists())

    @patch("garden_planning.views.get_or_cache_plant")
    @patch("garden_planning.views.fetch_plants_from_perenual")
    def test_one_invalid_plant_does_not_fail_other_recommendations(self, fetch_plants, cache_plant):
        valid_plant = Plant.objects.create(
            perenual_id=45679,
            name="Valid plant",
            description="A plant description.",
        )
        fetch_plants.side_effect = [[
            {"id": 45678, "common_name": "Invalid plant"},
            {"id": 45679, "common_name": "Valid plant"},
        ], [], []]

        def cache_candidate(candidate):
            if candidate["id"] == 45678:
                raise ValueError("Invalid candidate data")
            return valid_plant

        cache_plant.side_effect = cache_candidate
        response = self.client.post(
            self.url,
            data=json.dumps({"avg_rain_mm": 2, "avg_radiation": 18}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.json()["plants"]], ["Valid plant"])


class RecommendPlantsTimeBudgetTests(TestCase):
    """PWS stops a request after 30 s; slow Perenual calls must not reach that."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="budget", password="test-password")
        self.client.force_login(self.user)
        self.url = reverse("garden_planning:recommend_plants")
        self.body = json.dumps({"avg_rain_mm": 5.9, "avg_temp_c": 27.6, "avg_radiation": 21.9, "avg_humidity": 82})

    @patch("garden_planning.views.PERENUAL_TIME_BUDGET", 1)
    @patch("garden_planning.views.fetch_plant_details_from_perenual")
    @patch("garden_planning.views.fetch_plants_from_perenual")
    def test_slow_perenual_still_answers_within_budget(self, fetch_plants, fetch_details):
        import time

        def slow_page(**kwargs):
            time.sleep(3)
            return [{"id": 900 + kwargs["page"], "common_name": "Slow plant"}]

        fetch_plants.side_effect = slow_page
        started = time.monotonic()
        response = self.client.post(self.url, data=self.body, content_type="application/json")
        elapsed = time.monotonic() - started

        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 2.5)
        # Nothing arrived in time, so the built-in suggestions are shown instead.
        self.assertTrue(response.json()["plants"])
        fetch_details.assert_not_called()

    @patch("garden_planning.views.fetch_plant_details_from_perenual", return_value={"description": "Grows fast. Likes sun."})
    @patch("garden_planning.views.fetch_plants_from_perenual")
    def test_description_lookups_are_capped(self, fetch_plants, fetch_details):
        from garden_planning.views import MAX_DETAIL_LOOKUPS

        fetch_plants.side_effect = [[{"id": n, "common_name": f"Plant {n}"} for n in range(1, 9)], [], []]
        response = self.client.post(self.url, data=self.body, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["plants"]), 8)
        self.assertEqual(fetch_details.call_count, MAX_DETAIL_LOOKUPS)
        described = [p for p in response.json()["plants"] if p["description"] == "Grows fast."]
        self.assertEqual(len(described), MAX_DETAIL_LOOKUPS)


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
