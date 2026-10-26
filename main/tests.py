from django.test import TestCase

# Create your tests here.

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import GardenJournalEntry


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
