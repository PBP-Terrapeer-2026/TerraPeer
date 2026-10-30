"""Regression tests for validation, provider failures and optional seed safety.

Fixtures use the current care adapters; replace them when official models land.
"""

from datetime import date, datetime, timezone
from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError
from django.db import IntegrityError, transaction
from django.test import TestCase, SimpleTestCase, override_settings
from django.urls import reverse

from .forms import CareTaskForm
from .models import GardenSpace, Plant, CareTask
from .services import complete_task
from .weather import condition, forecast, ForecastUnavailable
from .templatetags.care_icons import icon


class CareBoundaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("boundary-owner")
        cls.garden = GardenSpace.objects.create(owner=cls.user, name="Balcony")
        cls.plant = Plant.objects.create(garden=cls.garden, name="Mint", pot="B")

    def test_invalid_timezone_rejected(self):
        self.garden.timezone_name = "Not/AZone"
        with self.assertRaises(ValidationError) as error:
            self.garden.full_clean()
        self.assertIn("timezone_name", error.exception.message_dict)

    def test_invalid_coordinates_rejected(self):
        for field, value in [("latitude", 91), ("longitude", -181)]:
            with self.subTest(field=field):
                garden = GardenSpace(owner=self.user, name="Bad", **{field: value})
                with self.assertRaises(ValidationError) as error:
                    garden.full_clean()
                self.assertIn(field, error.exception.message_dict)

    def test_local_day_uses_garden_timezone(self):
        with patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 1, 1, 18, tzinfo=timezone.utc),
        ):
            self.assertEqual(self.plant.today, date(2026, 1, 2))

    def test_interval_date_overflow_rejected_by_form(self):
        form = CareTaskForm(
            data={
                "action_type": "Watering",
                "due_date": "9999-12-31",
                "repeat": "every",
                "interval": 1,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("interval", form.errors)

    def test_completion_overflow_rolls_back_status(self):
        task = CareTask.objects.create(
            plant=self.plant,
            title="Water",
            action_type="Watering",
            due_date=date.max,
            repeat_every=1,
        )
        self.client.force_login(self.user)
        response = self.client.post(reverse("care:complete", args=[task.pk]))
        self.assertEqual(response.status_code, 409)
        task.refresh_from_db()
        self.assertEqual(task.status, "Pending")
        self.assertIsNone(task.completed_at)
        self.assertFalse(CareTask.objects.filter(previous=task).exists())

    def test_database_rejects_inconsistent_completion_and_repeat(self):
        for values in [{"status": "Completed"}, {"repeat_every": 0}]:
            with self.subTest(values=values):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    CareTask.objects.create(
                        plant=self.plant, title="Bad", due_date=date.today(), **values
                    )

    def test_database_rejects_second_successor(self):
        task = CareTask.objects.create(
            plant=self.plant, title="Water", due_date=date.today(), repeat_every=1
        )
        _, following, _ = complete_task(task.pk, self.user)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CareTask.objects.create(
                plant=self.plant,
                title="Duplicate",
                due_date=following.due_date,
                previous=task,
            )
        self.assertEqual(CareTask.objects.filter(previous=task).count(), 1)

    def test_empty_account_can_open_care(self):
        empty = get_user_model().objects.create_user("empty-owner")
        self.client.force_login(empty)
        response = self.client.get(reverse("care:choose"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "care/no_plants.html")

    def test_seed_missing_user_does_not_create_data(self):
        before = (
            GardenSpace.objects.count(),
            Plant.objects.count(),
            CareTask.objects.count(),
        )
        with self.assertRaises(CommandError):
            call_command("seed_terrapeer", username="missing", stdout=StringIO())
        self.assertEqual(
            before,
            (
                GardenSpace.objects.count(),
                Plant.objects.count(),
                CareTask.objects.count(),
            ),
        )

    def test_seed_twice_preserves_existing_edits_and_other_owner(self):
        other = get_user_model().objects.create_user("seed-other")
        call_command("seed_terrapeer", username=self.user.username, stdout=StringIO())
        task = CareTask.objects.get(
            plant__garden__owner=self.user, action_type="Watering"
        )
        task.instructions = "Personal instructions"
        task.save()
        call_command("seed_terrapeer", username=self.user.username, stdout=StringIO())
        task.refresh_from_db()
        self.assertEqual(task.instructions, "Personal instructions")
        self.assertEqual(
            CareTask.objects.filter(plant__garden__owner=self.user).count(), 3
        )
        self.assertFalse(GardenSpace.objects.filter(owner=other).exists())


@override_settings(
    WEATHER_DEMO=False,
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "care-boundary-weather",
        }
    },
)
class WeatherBoundaryTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.garden = SimpleNamespace(
            latitude=-6.4, longitude=106.8, timezone_name="Asia/Jakarta"
        )

    def payload(self):
        return {
            "daily": {
                "time": ["2026-10-29"],
                "weather_code": [3],
                "temperature_2m_min": [23],
                "temperature_2m_max": [31],
                "precipitation_probability_max": [40],
                "precipitation_sum": [2],
            }
        }

    @patch("care.weather.requests.get")
    def test_malformed_provider_data_not_cached(self, get):
        for payload in [
            {},
            {"daily": {}},
            {"daily": {"time": []}},
            {"daily": {"time": ["bad-date"]}},
            {"daily": None},
        ]:
            with self.subTest(payload=payload):
                get.return_value = Mock(json=Mock(return_value=payload))
                with self.assertRaises(ForecastUnavailable):
                    forecast(self.garden)
        get.return_value = Mock(json=Mock(return_value=self.payload()))
        self.assertEqual(forecast(self.garden)["days"][0]["high"], 31)
        self.assertEqual(get.call_count, 6)

    @patch("care.weather.requests.get")
    def test_http_failure_recovers_on_next_request(self, get):
        get.return_value.raise_for_status.side_effect = requests.HTTPError("503")
        with self.assertRaises(ForecastUnavailable):
            forecast(self.garden)
        get.return_value = Mock(json=Mock(return_value=self.payload()))
        self.assertEqual(forecast(self.garden)["state"], "ready")
        self.assertEqual(get.call_count, 2)

    @patch("care.weather.requests.get")
    def test_cache_separates_locations(self, get):
        get.return_value = Mock(json=Mock(return_value=self.payload()))
        forecast(self.garden)
        self.garden.latitude = -7.0
        forecast(self.garden)
        forecast(self.garden)
        self.assertEqual(get.call_count, 2)

    @override_settings(WEATHER_DEMO=True)
    @patch("care.weather.requests.get")
    def test_sample_weather_labelled_and_never_calls_provider(self, get):
        result = forecast(self.garden)
        self.assertTrue(result["demo"])
        self.assertEqual(len(result["days"]), 4)
        get.assert_not_called()

    def test_weather_categories_and_unknown_code(self):
        groups = [
            (0, "Sunny"),
            (2, "Partly cloudy"),
            (3, "Cloudy"),
            (45, "Foggy"),
            (51, "Drizzle"),
            (61, "Rainy"),
            (71, "Snow"),
            (95, "Thunderstorm"),
            (None, "Condition unavailable"),
            (999, "Condition unavailable"),
        ]
        for code, expected in groups:
            with self.subTest(code=code):
                self.assertEqual(condition(code)[0], expected)

    def test_icon_rejects_untrusted_path(self):
        self.assertEqual(icon("../../settings"), "")
        self.assertEqual(icon("<script>"), "")
