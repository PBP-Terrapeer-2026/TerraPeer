from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AuthFlowTests(TestCase):
    password = 'Sunflower-2026!'

    def setUp(self):
        self.user = get_user_model().objects.create_user('gardener', password=self.password)

    def test_pages_render_with_bootstrap_fields(self):
        for name in ('login', 'register'):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'class="form-control"')
                self.assertContains(response, 'csrfmiddlewaretoken')

    def test_register_creates_user_and_sends_to_login(self):
        response = self.client.post(reverse('register'), {
            'username': 'newbie', 'password1': self.password, 'password2': self.password,
        })
        self.assertRedirects(response, reverse('login'), fetch_redirect_response=False)
        self.assertTrue(get_user_model().objects.filter(username='newbie').exists())

    def test_register_keeps_next_for_login(self):
        response = self.client.post(reverse('register'), {
            'username': 'newbie', 'password1': self.password, 'password2': self.password, 'next': '/somewhere/',
        })
        self.assertEqual(response.url, reverse('login') + '?next=%2Fsomewhere%2F')

    def test_register_errors_are_shown(self):
        response = self.client.post(reverse('register'), {
            'username': 'newbie', 'password1': self.password, 'password2': 'different',
        })
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'is-invalid', status_code=400)

    def test_login_sets_cookie_and_follows_safe_next(self):
        response = self.client.post(reverse('login'), {
            'username': 'gardener', 'password': self.password, 'next': '/register/',
        })
        self.assertRedirects(response, '/register/', fetch_redirect_response=False)
        self.assertIn('last_login', response.cookies)

    def test_login_ignores_external_next(self):
        response = self.client.post(reverse('login'), {
            'username': 'gardener', 'password': self.password, 'next': 'https://evil.example/',
        })
        self.assertRedirects(response, reverse('show_main'), fetch_redirect_response=False)

    def test_wrong_password_shows_error(self):
        response = self.client.post(reverse('login'), {'username': 'gardener', 'password': 'nope'})
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'alert-danger', status_code=400)

    def test_signed_in_user_is_redirected_away_from_auth_pages(self):
        self.client.force_login(self.user)
        for name in ('login', 'register'):
            with self.subTest(page=name):
                self.assertRedirects(self.client.get(reverse(name)), reverse('show_main'), fetch_redirect_response=False)

    def test_logout_requires_post_and_clears_cookie(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('show_main'), fetch_redirect_response=False)
        self.assertEqual(response.cookies['last_login'].value, '')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_navbar_shows_account_menu_only_when_signed_in(self):
        self.assertContains(self.client.get(reverse('show_main')), 'Sign up free')
        self.client.force_login(self.user)
        response = self.client.get(reverse('show_main'))
        self.assertContains(response, 'Log out')
        self.assertNotContains(response, 'Sign up free')


class LandingPageTests(TestCase):
    def test_guest_landing_links_to_register_and_login(self):
        response = self.client.get(reverse("show_main"))
        self.assertTemplateUsed(response, "index.html")
        self.assertContains(response, f'cta-button" href="{reverse("register")}"')
        self.assertContains(response, f'href="{reverse("login")}">Already have an account? Log in')
        self.assertContains(response, "Create your account")
        self.assertNotContains(response, 'href="#"')

    def test_landing_has_no_explore_or_how_it_works_sections(self):
        response = self.client.get(reverse("show_main"))
        self.assertNotContains(response, "Explore plants")
        self.assertNotContains(response, "How it works")
        self.assertNotContains(response, "Browse plants before you sign up")

    def test_signed_in_landing_points_to_planning_and_setup(self):
        user = get_user_model().objects.create_user("cta-user", password="testing-only-9384")
        self.client.force_login(user)
        response = self.client.get(reverse("show_main"))
        self.assertContains(response, f'cta-button" href="{reverse("garden_planning:index")}"')
        self.assertContains(response, f'href="{reverse("garden_setup:space_list")}"')
        self.assertNotContains(response, "Already have an account? Log in")
