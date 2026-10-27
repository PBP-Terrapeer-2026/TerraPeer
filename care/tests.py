from datetime import timedelta
from unittest.mock import patch, Mock
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.cache import cache
import requests
from .models import GardenSpace, Plant, CareTask
from .forms import CareTaskForm
from .services import complete_task
from .weather import forecast, ForecastUnavailable


class CareTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            "owner", password="test-only-password"
        )
        cls.other = get_user_model().objects.create_user(
            "other", password="test-only-password"
        )
        cls.garden = GardenSpace.objects.create(
            owner=cls.user, name="Balcony", latitude=-6.4, longitude=106.8
        )
        cls.plant = Plant.objects.create(garden=cls.garden, name="Mint", pot="B")
        cls.second = Plant.objects.create(
            garden=cls.garden, name="Tomato", pot="A", image="tomato"
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.task = CareTask.objects.create(
            plant=self.plant,
            title="Water mint",
            action_type="Watering",
            due_date=self.plant.today - timedelta(days=1),
            repeat_every=3,
            instructions="Check first.",
        )

    def url(self, name, pk=None):
        return reverse("care:" + name, args=[pk or self.task.pk])

    def data(self, **overrides):
        data = {
            "action_type": "Watering",
            "due_date": str(self.plant.today),
            "repeat": "every",
            "interval": "3",
            "instructions": "Keep me",
        }
        data.update(overrides)
        return data

    def test_initial_page_and_templates(self):
        response = self.client.get(self.url("page", self.plant.pk))
        self.assertContains(response, "Care schedule")
        self.assertContains(response, "Overdue")
        for name in ["detail", "edit", "delete"]:
            self.assertIn("html", self.client.get(self.url(name)).json())

    def test_login_and_json_session_error(self):
        self.client.logout()
        self.assertEqual(
            self.client.get(self.url("page", self.plant.pk)).status_code, 302
        )
        self.assertEqual(
            self.client.get(self.url("list", self.plant.pk)).status_code, 401
        )

    def test_every_endpoint_scoped_to_owner(self):
        self.client.force_login(self.other)
        for name in ["detail", "edit", "delete"]:
            self.assertEqual(self.client.get(self.url(name)).status_code, 404)
        for name in ["edit", "delete", "complete"]:
            self.assertEqual(
                self.client.post(self.url(name), self.data()).status_code, 404
            )
        for name in ["page", "list", "weather", "add"]:
            self.assertEqual(
                self.client.get(self.url(name, self.plant.pk)).status_code, 404
            )

    def test_csrf_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.url("complete")).status_code, 403)

    def test_mutation_not_allowed_via_get(self):
        self.assertEqual(self.client.get(self.url("complete")).status_code, 405)

    def test_validation_keeps_values(self):
        response = self.client.post(
            self.url("add", self.plant.pk), self.data(interval="0", action_type="")
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("Keep me", response.json()["html"])
        self.assertIn('aria-invalid="true"', response.json()["html"])
        self.assertEqual(CareTask.objects.count(), 1)

    def test_fractional_negative_blank_interval(self):
        for value in ["-1", "1.5", "", "abc"]:
            form = CareTaskForm(self.data(interval=value))
            self.assertFalse(form.is_valid(), value)
            self.assertIn("interval", form.errors)

    def test_interval_one_and_optional_instructions(self):
        result = self.client.post(
            self.url("add", self.plant.pk), self.data(interval="1", instructions="")
        )
        self.assertEqual(result.status_code, 201)
        task = CareTask.objects.get(pk=result.json()["id"])
        self.assertEqual(task.repeat_label, "Every day")

    def test_no_repeat_discards_interval(self):
        result = self.client.post(
            self.url("add", self.plant.pk), self.data(repeat="none", interval="")
        )
        self.assertIsNone(CareTask.objects.get(pk=result.json()["id"]).repeat_every)

    def test_edit_interval_preserves_date_and_plant(self):
        original = self.task.due_date
        response = self.client.post(
            self.url("edit"),
            self.data(interval="5", due_date=str(original), plant=self.second.pk),
        )
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.plant, self.plant)
        self.assertEqual(self.task.due_date, original)
        self.assertEqual(self.task.title, "Water mint")
        _, next_task, _ = complete_task(self.task.pk, self.user)
        self.assertEqual(next_task.due_date, original + timedelta(days=5))

    def test_repeat_completion_idempotent_and_copies_fields(self):
        response = self.client.post(self.url("complete"))
        self.assertEqual(response.status_code, 200)
        self.client.post(self.url("complete"))
        self.assertEqual(CareTask.objects.count(), 2)
        self.task.refresh_from_db()
        self.assertIsNotNone(self.task.completed_at)
        following = self.task.next_task
        for name in ["plant", "title", "action_type", "instructions", "repeat_every"]:
            self.assertEqual(getattr(following, name), getattr(self.task, name))
        self.assertEqual(following.status, "Pending")

    def test_single_completion_makes_no_task(self):
        self.task.repeat_every = None
        self.task.save()
        self.client.post(self.url("complete"))
        self.assertEqual(CareTask.objects.count(), 1)

    def test_inactive_no_next_and_no_add(self):
        self.plant.status = "Finished"
        self.plant.save()
        self.client.post(self.url("complete"))
        self.assertEqual(CareTask.objects.count(), 1)
        self.assertEqual(
            self.client.post(self.url("add", self.plant.pk), self.data()).status_code,
            409,
        )

    def test_completed_cannot_edit(self):
        self.client.post(self.url("complete"))
        self.assertEqual(
            self.client.post(self.url("edit"), self.data()).status_code, 409
        )

    def test_delete_pending_keeps_history(self):
        _, following, _ = complete_task(self.task.pk, self.user)
        self.client.post(self.url("delete", following.pk))
        self.assertTrue(CareTask.objects.filter(pk=self.task.pk).exists())
        self.assertEqual(CareTask.objects.filter(status="Pending").count(), 0)

    def test_delete_completed_keeps_next(self):
        _, following, _ = complete_task(self.task.pk, self.user)
        self.client.post(self.url("delete"))
        following.refresh_from_db()
        self.assertIsNone(following.previous_id)
        self.assertEqual(following.status, "Pending")
        self.assertEqual(following.repeat_every, 3)

    def test_delete_get_does_not_mutate(self):
        self.client.get(self.url("delete"))
        self.assertTrue(CareTask.objects.filter(pk=self.task.pk).exists())

    def test_filters_intersect_and_scope(self):
        CareTask.objects.create(
            plant=self.plant,
            title="Upcoming",
            action_type="Inspection",
            due_date=self.plant.today + timedelta(days=1),
        )
        CareTask.objects.create(
            plant=self.second,
            title="Other plant task",
            action_type="Inspection",
            due_date=self.plant.today,
        )
        data = self.client.get(
            self.url("list", self.plant.pk), {"time": "upcoming", "status": "Pending"}
        ).json()["html"]
        self.assertIn("Upcoming", data)
        self.assertNotIn("Water mint", data)
        self.assertNotIn("Other plant task", data)
        data = self.client.get(
            self.url("list", self.plant.pk), {"time": "upcoming", "status": "Completed"}
        ).json()["html"]
        self.assertIn("No tasks match your filters.", data)

    def test_no_tasks_distinct_from_no_matches(self):
        data = self.client.get(self.url("list", self.second.pk)).json()["html"]
        self.assertIn("No care tasks yet", data)

    def test_pending_sorted_earliest_first(self):
        earlier = CareTask.objects.create(
            plant=self.plant,
            title="Earlier task",
            action_type="Pruning",
            due_date=self.plant.today - timedelta(days=3),
        )
        data = self.client.get(self.url("list", self.plant.pk)).json()["html"]
        self.assertLess(data.index(earlier.title), data.index(self.task.title))

    def test_xss_escaped(self):
        self.task.title = "<img src=x onerror=alert(1)>"
        self.task.instructions = "<script>alert(1)</script>"
        self.task.save()
        data = self.client.get(self.url("detail")).json()["html"]
        self.assertIn("&lt;script&gt;", data)
        self.assertNotIn("<script>", data)

    def test_htmx_fragment_alternative(self):
        response = self.client.get(
            self.url("list", self.plant.pk), HTTP_HX_REQUEST="true"
        )
        self.assertContains(response, "Water mint")
        self.assertTrue(response["Content-Type"].startswith("text/html"))

    def test_calendar_filters_owned_tasks_by_date(self):
        response = self.client.get(
            self.url("page", self.plant.pk), {"date": str(self.task.due_date)}
        )
        self.assertEqual(list(response.context["tasks"]), [self.task])
        self.assertEqual(len(response.context["calendar"]), 7)
        response = self.client.get(
            self.url("page", self.plant.pk), {"date": str(self.plant.today)}
        )
        self.assertEqual(list(response.context["tasks"]), [])

    def test_invalid_calendar_date_falls_back(self):
        for value in ["invalid", "9999-12-31", "0001-01-01"]:
            response = self.client.get(self.url("page", self.plant.pk), {"date": value})
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(response.context["selected_date"])

    def test_overdue_and_action_filters(self):
        response = self.client.get(
            self.url("list", self.plant.pk), {"overdue": "1", "action": "Inspection"}
        )
        self.assertNotIn("Water mint", response.json()["html"])
        response = self.client.get(
            self.url("list", self.plant.pk), {"overdue": "1", "action": "Watering"}
        )
        self.assertIn("Water mint", response.json()["html"])

    def test_calendar_summary_and_cards_share_ajax_response(self):
        self.client.post(self.url("complete"))
        response = self.client.get(self.url("list", self.plant.pk)).json()
        self.assertIn("calendar-card", response["calendar_html"])
        self.assertIn("summary-card", response["summary_html"])
        self.assertEqual(response["pending_count"], 1)
        self.assertIn("Completed", response["html"])

    def test_task_snapshot_has_constant_query_count(self):
        from django.test import RequestFactory
        from .views import list_context

        for offset in range(20):
            CareTask.objects.create(
                plant=self.plant,
                title=f"Task {offset}",
                action_type="Inspection",
                due_date=self.plant.today + timedelta(days=offset),
            )
        request = RequestFactory().get("/")
        # Plant+garden already loaded: totals, grouped calendar, selected tasks = 3.
        with self.assertNumQueries(3):
            context = list_context(request, self.plant)
            for task in context["tasks"]:
                _ = task.overdue  # Related plant/garden must not add N+1 queries.
        self.assertEqual(
            sum(day["count"] for day in context["calendar"]), context["week_total"]
        )

    def test_invalid_filters_are_normalized(self):
        response = self.client.get(
            self.url("page", self.plant.pk),
            {"time": "bad", "status": "bad", "action": "bad"},
        )
        self.assertEqual(response.context["time_filter"], "all")
        self.assertEqual(response.context["status_filter"], "all")
        self.assertEqual(response.context["action_filter"], "")

    def test_navigation_labels_and_unavailable_routes(self):
        response = self.client.get(self.url("page", self.plant.pk))
        items = response.context["care_nav_items"]
        self.assertEqual(
            [item["label"] for item in items],
            [
                "Home",
                "Garden Setup",
                "Planning",
                "My Plants",
                "Plant Care",
                "Journal",
                "Explore",
            ],
        )
        self.assertIsNone(items[1]["url"])
        self.assertEqual([item["key"] for item in items if item["active"]], ["care"])

    def test_demo_seed_refuses_normal_database(self):
        from django.core.management import call_command, CommandError

        with self.assertRaises(CommandError):
            call_command("prepare_care_demo")


@override_settings(WEATHER_DEMO=False)
class WeatherTests(TestCase):
    setUpTestData = CareTests.__dict__["setUpTestData"]
    url = CareTests.url

    def setUp(self):
        self.client.force_login(self.user)
        cache.clear()

    def sample(self):
        return {
            "daily": {
                "time": [str(self.plant.today)],
                "weather_code": [61],
                "temperature_2m_min": [24],
                "temperature_2m_max": [28],
                "precipitation_probability_max": [90],
                "precipitation_sum": [8],
            }
        }

    @patch("care.weather.requests.get")
    def test_live_parser_cache_units(self, get):
        get.return_value = Mock(json=lambda: self.sample())
        data = forecast(self.garden)
        self.assertEqual(data["days"][0]["mm"], 8)
        self.assertEqual(data["days"][0]["label"], "Rainy")
        forecast(self.garden)
        self.assertEqual(get.call_count, 1)
        self.assertEqual(get.call_args.kwargs["params"]["timezone"], "Asia/Jakarta")
        self.assertEqual(get.call_args.kwargs["params"]["precipitation_unit"], "mm")

    @patch("care.weather.requests.get", side_effect=requests.Timeout)
    def test_network_error_and_tasks_still_available(self, get):
        self.assertEqual(
            self.client.get(self.url("weather", self.plant.pk)).status_code, 503
        )
        self.assertEqual(
            self.client.get(self.url("list", self.plant.pk)).status_code, 200
        )

    @patch("care.weather.requests.get")
    def test_missing_values_are_not_zero(self, get):
        sample = self.sample()
        sample["daily"]["precipitation_sum"] = [None]
        get.return_value = Mock(json=lambda: sample)
        result = self.client.get(self.url("weather", self.plant.pk)).json()["html"]
        self.assertIn("— mm", result)

    @patch("care.weather.requests.get")
    def test_no_coordinates_skips_network(self, get):
        self.garden.latitude = None
        self.garden.save()
        self.assertEqual(forecast(self.garden)["state"], "no-location")
        get.assert_not_called()


class UndoTests(TestCase):
    setUpTestData = CareTests.__dict__["setUpTestData"]
    setUp = CareTests.setUp
    url = CareTests.url

    def test_undo_repeat_removes_generated_pending_and_can_complete_again(self):
        response = self.client.post(self.url("complete"))
        self.assertEqual(response.json()["undo_url"], self.url("undo"))
        follow_id = response.json()["next_id"]
        self.assertEqual(self.client.post(self.url("undo")).status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "Pending")
        self.assertIsNone(self.task.completed_at)
        self.assertFalse(CareTask.objects.filter(pk=follow_id).exists())
        self.assertEqual(CareTask.objects.count(), 1)
        # A repeated undo is harmless; completing again creates exactly one reminder.
        self.assertEqual(self.client.post(self.url("undo")).status_code, 200)
        self.client.post(self.url("complete"))
        self.assertEqual(CareTask.objects.count(), 2)

    def test_undo_single_task(self):
        self.task.repeat_every = None
        self.task.save()
        self.client.post(self.url("complete"))
        self.client.post(self.url("undo"))
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "Pending")
        self.assertIsNone(self.task.completed_at)
        self.assertEqual(CareTask.objects.count(), 1)

    def test_undo_refuses_to_delete_edited_followup(self):
        _, following, _ = complete_task(self.task.pk, self.user)
        following.instructions = "My deliberate change"
        following.save()
        result = self.client.post(self.url("undo"))
        self.assertEqual(result.status_code, 409)
        following.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(following.instructions, "My deliberate change")
        self.assertEqual(self.task.status, "Completed")
        self.assertIsNotNone(self.task.completed_at)

    def test_undo_refuses_completed_followup_and_keeps_descendants(self):
        _, following, _ = complete_task(self.task.pk, self.user)
        _, descendant, _ = complete_task(following.pk, self.user)
        self.assertEqual(self.client.post(self.url("undo")).status_code, 409)
        self.assertTrue(CareTask.objects.filter(pk=descendant.pk).exists())
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "Completed")
        self.assertEqual(CareTask.objects.count(), 3)

    def test_undo_after_followup_was_deleted(self):
        _, following, _ = complete_task(self.task.pk, self.user)
        following.delete()
        self.assertEqual(self.client.post(self.url("undo")).status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "Pending")

    def test_undo_requires_owner_and_login(self):
        self.client.post(self.url("complete"))
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.url("undo")).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.post(self.url("undo")).status_code, 401)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "Completed")

    def test_undo_requires_post_and_csrf(self):
        self.client.post(self.url("complete"))
        self.assertEqual(self.client.get(self.url("undo")).status_code, 405)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.user)
        self.assertEqual(protected.post(self.url("undo")).status_code, 403)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "Completed")

    def test_undo_inactive_plant_keeps_pending_without_followup(self):
        self.plant.status = "Finished"
        self.plant.save()
        self.client.post(self.url("complete"))
        self.assertEqual(self.client.post(self.url("undo")).status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "Pending")
        self.assertEqual(CareTask.objects.count(), 1)

    def test_done_tab_offers_undo_and_pending_filter_hides_completed(self):
        self.client.post(self.url("complete"))
        done = self.client.get(
            self.url("list", self.plant.pk), {"status": "Completed"}
        ).json()
        self.assertIn("data-undo=", done["html"])
        self.assertIn('aria-pressed="true"', done["html"])
        self.assertIn("data-task-id=", done["html"])
        self.client.post(self.url("undo"))
        done = self.client.get(
            self.url("list", self.plant.pk), {"status": "Completed"}
        ).json()
        self.assertNotIn("data-undo=", done["html"])
