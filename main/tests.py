from django.test import TestCase

# Create your tests here.

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from .models import GardenJournalEntry
from datetime import timedelta
from django.utils import timezone


class GardenJournalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="journal_owner",
            password="TestPassword123!",
        )
        self.other_user = User.objects.create_user(
            username="another_user",
            password="TestPassword123!",
        )

        self.entry = GardenJournalEntry.objects.create(
            user=self.user,
            plant_name="Basil",
            entry_type="growth",
            title="New leaves appeared",
            notes="The basil plant has two new leaves.",
        )

    def test_journal_requires_login(self):
        response = self.client.get(
            reverse("garden_journal")
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_user_only_sees_own_entries(self):
        GardenJournalEntry.objects.create(
            user=self.other_user,
            plant_name="Rose",
            entry_type="flowering",
            title="Private rose journal",
            notes="This belongs to another user.",
        )

        self.client.login(
            username="journal_owner",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("garden_journal")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "New leaves appeared",
        )
        self.assertNotContains(
            response,
            "Private rose journal",
        )

    def test_create_entry_belongs_to_logged_in_user(self):
        self.client.login(
            username="journal_owner",
            password="TestPassword123!",
        )

        response = self.client.post(
            reverse("garden_journal_create"),
            {
                "plant_name": "Mint",
                "entry_date": "2026-10-25",
                "entry_type": "growth",
                "title": "Mint is growing",
                "notes": "New mint leaves appeared.",
                "harvest_quantity": "",
                "harvest_unit": "",
                "weather_summary": "Sunny",
            },
        )

        self.assertEqual(response.status_code, 302)

        entry = GardenJournalEntry.objects.get(
            title="Mint is growing"
        )

        self.assertEqual(entry.user, self.user)

    def test_cannot_edit_another_users_entry(self):
        self.client.login(
            username="another_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "garden_journal_edit",
                args=[self.entry.pk],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_cannot_delete_another_users_entry(self):
        self.client.login(
            username="another_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "garden_journal_delete",
                args=[self.entry.pk],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_edit_own_entry(self):
        self.client.login(
            username="journal_owner",
            password="TestPassword123!",
        )

        response = self.client.post(
            reverse(
                "garden_journal_edit",
                args=[self.entry.pk],
            ),
            {
                "plant_name": "Basil",
                "entry_date": "2026-10-25",
                "entry_type": "growth",
                "title": "Basil is thriving",
                "notes": "The plant has several new leaves.",
                "harvest_quantity": "",
                "harvest_unit": "",
                "weather_summary": "Sunny",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.entry.refresh_from_db()
        self.assertEqual(
            self.entry.title,
            "Basil is thriving",
        )

    def test_delete_own_entry(self):
        self.client.login(
            username="journal_owner",
            password="TestPassword123!",
        )

        response = self.client.post(
            reverse(
                "garden_journal_delete",
                args=[self.entry.pk],
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            GardenJournalEntry.objects.filter(
                pk=self.entry.pk
            ).exists()
        )

    
    def test_search_filters_journal_entries(self):
        self.client.login(
            username="journal_owner",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("garden_journal"),
            {"q": "New leaves"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["entries"]),
            [self.entry],
        )

    def test_filter_by_plant(self):
        mint_entry = GardenJournalEntry.objects.create(
            user=self.user,
            plant_name="Mint",
            entry_type="growth",
            title="Mint is growing",
            notes="New mint leaves appeared.",
        )

        self.client.login(
            username="journal_owner",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("garden_journal"),
            {"plant": "Mint", "period": "all"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["entries"]),
            [mint_entry],
        )

    def test_filter_by_event_type(self):
        harvest_entry = GardenJournalEntry.objects.create(
            user=self.user,
            plant_name="Basil",
            entry_type="harvest",
            title="First harvest",
            notes="Collected fresh basil leaves.",
        )

        self.client.login(
            username="journal_owner",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("garden_journal"),
            {"event": "harvest", "period": "all"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["entries"]),
            [harvest_entry],
        )

    def test_all_period_includes_older_entries(self):
        from datetime import date

        old_entry = GardenJournalEntry.objects.create(
            user=self.user,
            plant_name="Rose",
            entry_type="flowering",
            title="An older rose entry",
            notes="The rose was flowering.",
            entry_date=date(2026, 1, 1),
        )

        self.client.login(
            username="journal_owner",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("garden_journal"),
            {"period": "all"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            old_entry,
            response.context["entries"],
        )

    #testing garden evaluation
    
class GardenJournalEvaluationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="evaluation_owner",
            password="TestPassword123!",
        )
        self.other_user = User.objects.create_user(
            username="evaluation_other",
            password="TestPassword123!",
        )

        self.today = timezone.localdate()
        self.current_month = self.today.replace(day=1)
        self.previous_month = (
            self.current_month - timedelta(days=1)
        ).replace(day=1)

        self.entry = GardenJournalEntry.objects.create(
            user=self.user,
            plant_name="Basil",
            entry_date=self.today,
            entry_type="growth",
            title="New basil leaves",
            notes="Several new leaves appeared.",
        )

    def test_evaluation_requires_login(self):
        response = self.client.get(
            reverse("garden_journal_evaluation")
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_evaluation_counts_only_selected_month(self):
        GardenJournalEntry.objects.create(
            user=self.user,
            plant_name="Tomato",
            entry_date=self.previous_month.replace(day=10),
            entry_type="harvest",
            title="Tomato harvest",
            notes="Collected ripe tomatoes.",
            harvest_quantity="2.00",
            harvest_unit="kg",
        )

        self.client.login(
            username="evaluation_owner",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("garden_journal_evaluation"),
            {
                "month": self.previous_month.strftime("%Y-%m"),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_entries"], 1)
        self.assertEqual(response.context["harvest_count"], 1)
        self.assertEqual(response.context["plant_count"], 1)
        self.assertEqual(
            response.context["selected_month"],
            self.previous_month.strftime("%Y-%m"),
        )

    def test_evaluation_excludes_other_users_entries(self):
        GardenJournalEntry.objects.create(
            user=self.other_user,
            plant_name="Rose",
            entry_date=self.today,
            entry_type="issue",
            title="Private rose issue",
            notes="This belongs to another user.",
        )

        self.client.login(
            username="evaluation_owner",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("garden_journal_evaluation"),
            {
                "month": self.current_month.strftime("%Y-%m"),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_entries"], 1)
        self.assertEqual(response.context["problem_count"], 0)
        self.assertNotContains(response, "Private rose issue")

    def test_evaluation_handles_month_without_entries(self):
        self.client.login(
            username="evaluation_owner",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("garden_journal_evaluation"),
            {
                "month": self.previous_month.strftime("%Y-%m"),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_entries"], 0)
        self.assertEqual(response.context["harvest_count"], 0)
        self.assertEqual(response.context["problem_count"], 0)
        self.assertEqual(response.context["plant_count"], 0)
        self.assertEqual(len(response.context["plant_summary"]), 0)
        self.assertTrue(
            all(
                week["count"] == 0
                for week in response.context["weekly_activity"]
            )
        )

    def test_evaluation_aggregates_entries_by_plant(self):
        GardenJournalEntry.objects.create(
            user=self.user,
            plant_name="Basil",
            entry_date=self.today,
            entry_type="harvest",
            title="Basil harvest",
            notes="Collected basil leaves.",
            harvest_quantity="100.00",
            harvest_unit="g",
        )

        self.client.login(
            username="evaluation_owner",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("garden_journal_evaluation"),
            {
                "month": self.current_month.strftime("%Y-%m"),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_entries"], 2)
        self.assertEqual(response.context["harvest_count"], 1)

        basil_summary = next(
            item
            for item in response.context["plant_summary"]
            if item["plant_name"] == "Basil"
        )

        self.assertEqual(basil_summary["entry_count"], 2)
        self.assertEqual(basil_summary["harvest_count"], 1)
        self.assertEqual(basil_summary["issue_count"], 0)


