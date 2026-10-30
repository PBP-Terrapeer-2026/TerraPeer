"""Contracts with merged modules, including old tasks and ownership boundaries."""

from datetime import timedelta
from unittest.mock import Mock, patch

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from my_plants.models import Plant
from .integration import plant_space
from .models import CareTask, PlantCareSpace, LegacyPlant, LegacyGardenSpace
from .test_helpers import make_plant, make_space


class OfficialIntegrationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("care-owner")
        self.other = get_user_model().objects.create_user("care-other")
        self.space = make_space(self.user)
        self.foreign_space = make_space(self.other, name="Private garden")
        self.plant = make_plant(self.user)
        self.foreign_plant = make_plant(self.other)
        self.client.force_login(self.user)
        cache.clear()

    def test_real_plants_appear_without_copying_adapters(self):
        self.assertRedirects(
            self.client.get(reverse("care:choose")),
            reverse("care:page", args=[self.plant.pk]),
        )
        self.assertEqual(LegacyPlant.objects.count(), 0)
        response = self.client.get(reverse("care:page", args=[self.plant.pk]))
        self.assertEqual(list(response.context["plants"]), [self.plant])
        self.assertNotContains(response, "Private garden")
        self.assertContains(response, reverse("garden_setup:space_list"))
        self.assertContains(response, reverse("garden_planning:index"))
        self.assertContains(response, 'action="' + reverse("logout") + '"')
        self.assertNotContains(response, ">Explore<")
        self.assertContains(response, "bootstrap.bundle.min.js", count=1)

    def test_space_requires_owner_login_post_and_csrf(self):
        url = reverse("care:set-space", args=[self.plant.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(
            self.client.post(url, {"growing_space": self.foreign_space.pk}).status_code,
            422,
        )
        self.assertFalse(PlantCareSpace.objects.exists())
        self.assertEqual(
            self.client.post(
                reverse("care:set-space", args=[self.foreign_plant.pk]),
                {"growing_space": self.space.pk},
            ).status_code,
            404,
        )
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.user)
        self.assertEqual(
            protected.post(url, {"growing_space": self.space.pk}).status_code, 403
        )
        self.client.logout()
        self.assertEqual(
            self.client.post(url, {"growing_space": self.space.pk}).status_code, 401
        )

    @override_settings(WEATHER_DEMO=False)
    @patch("plant_care.weather.requests.get")
    def test_official_space_coordinates_reach_weather_provider(self, get):
        get.return_value = Mock(
            json=lambda: {
                "daily": {
                    "time": [str(timezone.localdate())],
                    "weather_code": [61],
                    "temperature_2m_min": [23],
                    "temperature_2m_max": [28],
                    "precipitation_probability_max": [90],
                    "precipitation_sum": [8],
                }
            }
        )
        space_url = reverse("care:set-space", args=[self.plant.pk])
        weather_url = reverse("care:weather", args=[self.plant.pk])
        self.assertIn(
            "Garden location needed", self.client.get(weather_url).json()["html"]
        )
        get.assert_not_called()
        self.assertEqual(
            self.client.post(space_url, {"growing_space": self.space.pk}).status_code,
            200,
        )
        response = self.client.get(weather_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Rainy", response.json()["html"])
        params = get.call_args.kwargs["params"]
        self.assertEqual(float(params["latitude"]), -6.4)
        self.assertEqual(float(params["longitude"]), 106.8)
        self.assertEqual(params["timezone"], self.space.timezone)
        self.assertEqual(
            self.client.post(space_url, {"growing_space": ""}).status_code, 200
        )
        self.assertIn(
            "Garden location needed", self.client.get(weather_url).json()["html"]
        )

    def test_foreign_association_is_rejected_by_validation_and_ignored_on_read(self):
        link = PlantCareSpace(plant=self.plant, growing_space=self.foreign_space)
        with self.assertRaises(ValidationError):
            link.full_clean()
        link.save()  # Simulate data inserted by an external integration bypassing forms.
        self.plant.refresh_from_db()
        self.assertIsNone(plant_space(self.plant))

    def test_deleted_space_keeps_tasks_and_clears_weather_location(self):
        PlantCareSpace.objects.create(plant=self.plant, growing_space=self.space)
        task = CareTask.objects.create(
            plant=self.plant,
            title="Water",
            action_type="Watering",
            due_date=timezone.localdate(),
        )
        self.space.delete()
        self.plant.refresh_from_db()
        self.assertIsNone(plant_space(self.plant))
        self.assertTrue(CareTask.objects.filter(pk=task.pk).exists())

    def test_my_plants_deletion_reports_protected_task(self):
        CareTask.objects.create(
            plant=self.plant, title="Water", due_date=timezone.localdate()
        )
        response = self.client.post(
            reverse("my_plants:delete", args=[self.plant.pk]),
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertTrue(Plant.objects.filter(pk=self.plant.pk).exists())

    def test_legacy_link_keeps_history_and_successor_then_hides_notice(self):
        garden = LegacyGardenSpace.objects.create(owner=self.user, name="Old balcony")
        old = LegacyPlant.objects.create(garden=garden, name="Mint", pot="B")
        first = CareTask.objects.create(
            legacy_plant=old,
            title="Old water",
            due_date=timezone.localdate(),
            status="Completed",
            completed_at=timezone.now(),
            repeat_every=3,
        )
        following = CareTask.objects.create(
            legacy_plant=old,
            title="Old water",
            due_date=timezone.localdate() + timedelta(days=3),
            previous=first,
            repeat_every=3,
        )
        url = reverse("care:link-legacy")
        self.assertContains(
            self.client.get(reverse("care:page", args=[self.plant.pk])),
            "Connect them to My Plants",
        )
        invalid = self.client.post(
            url, {"legacy_plant": old.pk, "plant": self.foreign_plant.pk}
        )
        self.assertTrue(invalid.context["form"].errors)
        first.refresh_from_db()
        self.assertIsNone(first.plant_id)
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(url), "Old balcony")
        invalid = self.client.post(
            url, {"legacy_plant": old.pk, "plant": self.foreign_plant.pk}
        )
        self.assertTrue(invalid.context["form"].errors)
        self.client.force_login(self.user)
        self.assertRedirects(
            self.client.post(url, {"legacy_plant": old.pk, "plant": self.plant.pk}),
            reverse("care:page", args=[self.plant.pk]),
        )
        first.refresh_from_db()
        following.refresh_from_db()
        self.assertEqual(first.status, "Completed")
        self.assertEqual(first.plant_id, self.plant.pk)
        self.assertEqual(following.plant_id, self.plant.pk)
        self.assertEqual(following.previous_id, first.pk)
        self.assertEqual(first.legacy_plant_id, old.pk)
        self.assertNotContains(
            self.client.get(reverse("care:page", args=[self.plant.pk])),
            "Connect them to My Plants",
        )

    def test_renamed_package_keeps_migration_label_and_table(self):
        self.assertEqual(apps.get_app_config("care").name, "plant_care")
        self.assertEqual(CareTask._meta.db_table, "care_caretask")


class CareMigrationTests(TransactionTestCase):
    def test_existing_ids_and_task_links_survive_without_guessing_official_ids(self):
        before = [("care", "0002_protect_task_plant")]
        after = [("care", "0003_official_plants_and_care_location")]
        executor = MigrationExecutor(connection)
        leafs = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(before)
            old_apps = executor.loader.project_state(before).apps
            User = old_apps.get_model("auth", "User")
            owner = User.objects.create(username="migration-owner")
            garden = old_apps.get_model("care", "GardenSpace").objects.create(
                owner_id=owner.pk, name="Old garden"
            )
            old = old_apps.get_model("care", "Plant").objects.create(
                garden_id=garden.pk, name="Old mint", pot="B"
            )
            Task = old_apps.get_model("care", "CareTask")
            first = Task.objects.create(
                plant_id=old.pk,
                title="Keep history",
                due_date=timezone.localdate(),
                status="Completed",
                completed_at=timezone.now(),
            )
            second = Task.objects.create(
                plant_id=old.pk,
                title="Keep next",
                due_date=timezone.localdate(),
                previous_id=first.pk,
            )
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            new_apps = executor.loader.project_state(after).apps
            official = new_apps.get_model("my_plants", "Plant").objects.create(
                id=old.pk,
                owner_id=owner.pk,
                name="Different official plant",
                species_name="Basil",
            )
            migrated = new_apps.get_model("care", "CareTask").objects.get(pk=first.pk)
            successor = new_apps.get_model("care", "CareTask").objects.get(pk=second.pk)
            self.assertIsNone(migrated.plant_id)
            self.assertEqual(migrated.legacy_plant_id, old.pk)
            self.assertEqual(migrated.status, "Completed")
            self.assertEqual(successor.previous_id, first.pk)
            self.assertEqual(
                new_apps.get_model("care", "LegacyPlant").objects.get(pk=old.pk).name,
                "Old mint",
            )
        finally:
            MigrationExecutor(connection).migrate(leafs)
