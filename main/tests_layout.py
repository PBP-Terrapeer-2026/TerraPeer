from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class SharedLayoutTests(TestCase):
    """Every module renders the same navbar once and loads Bootstrap JS once.

    A second copy of bootstrap.bundle toggles dropdowns twice, so the account
    menu (and its Log out button) would not open.
    """

    def setUp(self):
        user = get_user_model().objects.create_user("layout", password="testing-only-9384")
        self.client.force_login(user)

    def test_each_module_has_one_navbar_and_one_bootstrap_bundle(self):
        urls = [
            reverse("show_main"),
            reverse("garden_setup:space_list"),
            reverse("garden_planning:index"),
            reverse("my_plants:list"),
            reverse("care:choose"),
            reverse("garden_journal"),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "bootstrap.bundle", count=1)
                self.assertContains(response, 'aria-label="Main navigation"', count=1)
                self.assertContains(response, "tp-account", count=1)
