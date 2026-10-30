from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase, override_settings

from my_plants.models import Plant


@override_settings(DEBUG=False)
class ErrorPageTests(TestCase):
    def test_unknown_url_uses_branded_404(self):
        response = self.client.get("/no-such-page/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "We couldn't find that page", status_code=404)
        self.assertContains(response, 'aria-label="Main navigation"', status_code=404)

    def test_other_users_plant_shows_branded_404(self):
        owner = get_user_model().objects.create_user("owner", password="testing-only-9384")
        other = get_user_model().objects.create_user("other", password="testing-only-9384")
        plant = Plant.objects.create(owner=owner, name="Basil", species_name="Ocimum", planted_on="2026-10-01")
        self.client.force_login(other)
        response = self.client.get(plant.get_absolute_url())
        self.assertContains(response, "belongs to another account", status_code=404)
        self.assertContains(response, "Go to My Plants", status_code=404)

    def test_500_page_renders_without_request_context(self):
        html = render_to_string("500.html")
        self.assertIn("Something went wrong on our side", html)
