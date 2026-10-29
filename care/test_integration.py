from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class ProjectIntegrationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "integration", password="testing-only-9384"
        )

    def test_existing_auth_then_care_navigation(self):
        response = self.client.post(
            "/login/",
            {
                "username": "integration",
                "password": "testing-only-9384",
                "next": "/plant-care/",
            },
        )
        self.assertRedirects(response, reverse("show_main"))
        page = self.client.get("/plant-care/")
        self.assertContains(page, "Your plants will appear here")
        self.assertContains(page, "css/style.css")
        self.assertTemplateUsed(page, "base.html")
        self.assertContains(self.client.get("/"), 'href="/plant-care/"')

    def test_existing_auth_keeps_group_landing_destination(self):
        response = self.client.post(
            "/login/",
            {
                "username": "integration",
                "password": "testing-only-9384",
                "next": "https://example.org/",
            },
        )
        self.assertRedirects(response, reverse("show_main"))

    def test_home_redirect_uses_group_landing(self):
        self.assertRedirects(
            self.client.get(reverse("care:landing")), reverse("show_main")
        )

    def test_care_uses_common_base_without_duplicate_main_or_navigation(self):
        from care.models import GardenSpace, Plant

        garden = GardenSpace.objects.create(owner=self.user, name="Test balcony")
        plant = Plant.objects.create(garden=garden, name="Mint", pot="A")
        self.client.force_login(self.user)
        page = self.client.get(reverse("care:page", args=[plant.pk]))
        self.assertTemplateUsed(page, "base.html")
        self.assertTemplateNotUsed(page, "terrapeer/base.html")
        self.assertContains(page, 'id="main-content"', count=1)
        self.assertContains(page, 'aria-label="Main navigation"', count=1)
        self.assertContains(page, 'id="modal-root"', count=1)
        self.assertContains(page, "terrapeer/css/care-final.css")
        self.assertContains(page, "terrapeer/js/plant-care.js")
        home = self.client.get("/")
        login = self.client.get("/login/")
        for response in (home, login):
            self.assertNotContains(response, "terrapeer/css/care-final.css")
            self.assertNotContains(response, 'class="care-topbar')

    def test_login_without_next_parameter_renders(self):
        response = self.client.get("/login/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "login.html")
