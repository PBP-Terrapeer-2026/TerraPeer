from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from unittest.mock import patch
from .forms import GrowingSpaceForm
from .models import GrowingSpace
from .geocoding import GeocodingServiceError

class GrowingSpaceFormTest(TestCase):
    def setUp(self):
        self.valid_data = {
            "name": "My Balcony",
            "environment": "outdoor",
            "space_type": "balcony",
            "geocoding_id": 123456,
            "city": "Depok",
            "region": "West Java",
            "country": "Indonesia",
            "latitude": "-6.402500",
            "longitude": "106.794200",
            "timezone": "Asia/Jakarta",
            "sunlight_range": "4-6",
            "light_exposure": "direct",
            "growing_medium": "soil",
            "rain_access": "exposed",
            "support_available": "yes",
            "pot_capacity": 4,
            "care_availability": "daily",
            "notes": "Morning sunlight.",
        }

    def test_valid_form(self):
        form = GrowingSpaceForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_does_not_expose_user(self):
        form = GrowingSpaceForm()
        self.assertNotIn("user", form.fields)

    def test_invalid_capacity(self):
        data = self.valid_data.copy()
        data["pot_capacity"] = 0
        form = GrowingSpaceForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("pot_capacity", form.errors)

    def test_indoor_exposed_is_invalid(self):
        data = self.valid_data.copy()
        data["environment"] = "indoor"
        form = GrowingSpaceForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("rain_access", form.errors)

    def test_location_is_required(self):
        data = self.valid_data.copy()
        data["geocoding_id"] = ""
        form = GrowingSpaceForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("geocoding_id", form.errors)

    def test_bootstrap_classes_are_applied(self):
        form = GrowingSpaceForm()

        self.assertIn(
            "form-control",
            form.fields["name"].widget.attrs["class"],
        )
        self.assertIn(
            "form-select",
            form.fields["environment"].widget.attrs["class"],
        )

    def test_admin_registration(self):
        self.assertTrue(
            admin.site.is_registered(GrowingSpace)
        )

    def test_terrace_space_type(self):
        data = self.valid_data.copy()
        data["space_type"] = "terrace"

        form = GrowingSpaceForm(data=data)

        self.assertTrue(form.is_valid(), form.errors)

    def test_indoor_windowsill(self):
        data = self.valid_data.copy()
        data["environment"] = "indoor"
        data["space_type"] = "windowsill"
        data["rain_access"] = "sheltered"

        form = GrowingSpaceForm(data=data)

        self.assertTrue(form.is_valid(), form.errors)

    def test_soil_mix_medium(self):
        data = self.valid_data.copy()
        data["growing_medium"] = "soil_mix"

        form = GrowingSpaceForm(data=data)

        self.assertTrue(form.is_valid(), form.errors)

    def test_rarely_care_availability(self):
        data = self.valid_data.copy()
        data["care_availability"] = "rarely"

        form = GrowingSpaceForm(data=data)

        self.assertTrue(form.is_valid(), form.errors)
    
    def test_indoor_room_not_in_form_choices(self):
        form = GrowingSpaceForm()
        choices = [value for value, label in form.fields["space_type"].choices]

        self.assertNotIn("room", choices)
        self.assertIn("other", choices)

    def test_other_space_type_requires_description(self):
        data = self.valid_data.copy()
        data["space_type"] = "other"
        data["other_space_type"] = ""

        form = GrowingSpaceForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("other_space_type", form.errors)

    def test_other_space_type_accepts_description(self):
        data = self.valid_data.copy()
        data["space_type"] = "other"
        data["other_space_type"] = "Greenhouse"

        form = GrowingSpaceForm(data=data)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["other_space_type"], "Greenhouse")

    def test_other_description_cleared_for_normal_type(self):
        data = self.valid_data.copy()
        data["space_type"] = "balcony"
        data["other_space_type"] = "Greenhouse"

        form = GrowingSpaceForm(data=data)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["other_space_type"], "")

class GrowingSpaceModelTest(TestCase):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="garden_tester",
            password="test-password-123",
        )
        self.valid_data = {
            "user": self.user,
            "name": "My Balcony",
            "environment": "outdoor",
            "space_type": "balcony",
            "geocoding_id": 123456,
            "city": "Depok",
            "region": "West Java",
            "country": "Indonesia",
            "latitude": Decimal("-6.402500"),
            "longitude": Decimal("106.794200"),
            "timezone": "Asia/Jakarta",
            "sunlight_range": "4-6",
            "light_exposure": "direct",
            "growing_medium": "soil",
            "rain_access": "exposed",
            "support_available": "yes",
            "pot_capacity": 4,
            "care_availability": "daily",
            "notes": "Morning sunlight.",
        }

    def test_create_valid_growing_space(self):
        space = GrowingSpace(**self.valid_data)
        space.full_clean()
        space.save()

        self.assertIsNotNone(space.pk)
        self.assertEqual(space.name, "My Balcony")
        self.assertEqual(space.pot_capacity, 4)
        self.assertEqual(space.user, self.user)

    def test_space_is_associated_with_its_owner(self):
        space = GrowingSpace.objects.create(
            **self.valid_data
        )
        self.assertIn(
            space,
            self.user.growing_spaces.all(),
        )

    def test_pot_capacity_cannot_be_zero(self):
        data = self.valid_data.copy()
        data["pot_capacity"] = 0
        space = GrowingSpace(**data)

        with self.assertRaises(ValidationError):
            space.full_clean()

    def test_pot_capacity_cannot_exceed_100(self):
        data = self.valid_data.copy()
        data["pot_capacity"] = 101
        space = GrowingSpace(**data)

        with self.assertRaises(ValidationError):
            space.full_clean()

    def test_indoor_space_cannot_be_rain_exposed(self):
        data = self.valid_data.copy()
        data["environment"] = "indoor"
        space = GrowingSpace(**data)

        with self.assertRaises(ValidationError):
            space.full_clean()

    def test_short_space_name_is_rejected(self):
        data = self.valid_data.copy()
        data["name"] = "A"
        space = GrowingSpace(**data)

        with self.assertRaises(ValidationError):
            space.full_clean()

    def test_invalid_latitude_is_rejected(self):
        data = self.valid_data.copy()
        data["latitude"] = Decimal("95.000000")
        space = GrowingSpace(**data)

        with self.assertRaises(ValidationError):
            space.full_clean()

class GrowingSpaceOverviewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(
            username="overview_owner", password="test-pass-123"
        )
        self.other = User.objects.create_user(
            username="overview_other", password="test-pass-123"
        )
        self.url = reverse("garden_setup:space_list")

        base = {
            "environment": "outdoor",
            "space_type": "balcony",
            "geocoding_id": 123456,
            "city": "Depok",
            "region": "West Java",
            "country": "Indonesia",
            "latitude": Decimal("-6.402500"),
            "longitude": Decimal("106.794200"),
            "timezone": "Asia/Jakarta",
            "sunlight_range": "4-6",
            "light_exposure": "direct",
            "growing_medium": "soil",
            "rain_access": "exposed",
            "support_available": "yes",
            "pot_capacity": 4,
            "care_availability": "daily",
        }
        GrowingSpace.objects.create(user=self.owner, name="My Balcony", **base)

        indoor = base.copy()
        indoor.update(
            environment="indoor",
            space_type="windowsill",
            rain_access="sheltered",
            city="Bandung",
        )
        GrowingSpace.objects.create(user=self.owner, name="Kitchen Window", **indoor)

        private = base.copy()
        private.update(city="Jakarta", space_type="rooftop")
        GrowingSpace.objects.create(user=self.other, name="Private Rooftop", **private)

    def test_guests_are_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_owner_sees_only_their_spaces(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "garden_setup/space_list.html")
        self.assertContains(response, "My Balcony")
        self.assertContains(response, "Kitchen Window")
        self.assertNotContains(response, "Private Rooftop")

    def test_search_by_name(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url, {"q": "balcony"})
        self.assertContains(response, "My Balcony")
        self.assertNotContains(response, "Kitchen Window")

    def test_search_by_city(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url, {"q": "Bandung"})
        self.assertContains(response, "Kitchen Window")
        self.assertNotContains(response, "My Balcony")

    def test_filter_indoor(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url, {"environment": "indoor"})
        self.assertContains(response, "Kitchen Window")
        self.assertNotContains(response, "My Balcony")

    def test_search_no_results(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url, {"q": "lavender"})
        self.assertContains(response, "No matching growing spaces")
        self.assertNotContains(response, "My Balcony")

    def test_empty_overview(self):
        User = get_user_model()
        empty_user = User.objects.create_user(
            username="overview_empty", password="test-pass-123"
        )
        self.client.force_login(empty_user)
        response = self.client.get(self.url)
        self.assertContains(response, "No growing spaces yet")

class GrowingSpaceCreateEditTest(TestCase):
    def setUp(self):
        User = get_user_model()

        self.owner = User.objects.create_user(
            username="form_owner",
            password="test-pass-123",
        )

        self.other = User.objects.create_user(
            username="form_other",
            password="test-pass-123",
        )

        self.create_url = reverse(
            "garden_setup:space_create"
        )

        self.search_url = reverse(
            "garden_setup:location_search"
        )

        self.location = {
            "id": 123456,
            "name": "Depok",
            "region": "West Java",
            "country": "Indonesia",
            "latitude": "-6.402500",
            "longitude": "106.794200",
            "timezone": "Asia/Jakarta",
        }

        self.data = {
            "name": "My Balcony",
            "environment": "outdoor",
            "space_type": "balcony",
            "geocoding_id": "123456",
            "city": "Depok",
            "region": "",
            "country": "",
            "latitude": "",
            "longitude": "",
            "timezone": "",
            "sunlight_range": "4-6",
            "light_exposure": "direct",
            "growing_medium": "soil",
            "rain_access": "exposed",
            "support_available": "yes",
            "pot_capacity": "4",
            "care_availability": "daily",
            "notes": "",
        }

    def make_space(self, user=None):
        return GrowingSpace.objects.create(
            user=user or self.owner,
            name="My Balcony",
            environment="outdoor",
            space_type="balcony",
            geocoding_id=123456,
            city="Depok",
            region="West Java",
            country="Indonesia",
            latitude=Decimal("-6.402500"),
            longitude=Decimal("106.794200"),
            timezone="Asia/Jakarta",
            sunlight_range="4-6",
            light_exposure="direct",
            growing_medium="soil",
            rain_access="exposed",
            support_available="yes",
            pot_capacity=4,
            care_availability="daily",
            notes="",
        )

    def test_create_requires_login(self):
        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse("login"),
            response["Location"],
        )

    def test_create_form_loads(self):
        self.client.force_login(self.owner)

        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "garden_setup/space_form.html",
        )
        self.assertContains(
            response,
            "Create Growing Space",
        )

    @patch("garden_setup.views.get_location_by_id")
    def test_create_saves_space(self, mock_location):
        mock_location.return_value = self.location

        self.client.force_login(self.owner)

        response = self.client.post(
            self.create_url,
            self.data,
        )

        self.assertRedirects(
            response,
            reverse("garden_setup:space_list"),
        )

        space = GrowingSpace.objects.get(
            name="My Balcony"
        )

        self.assertEqual(space.user, self.owner)
        self.assertEqual(space.city, "Depok")
        self.assertEqual(
            space.latitude,
            Decimal("-6.402500"),
        )

    def test_create_requires_valid_location(self):
        self.client.force_login(self.owner)

        data = self.data.copy()
        data["geocoding_id"] = ""

        response = self.client.post(
            self.create_url,
            data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            GrowingSpace.objects.count(),
            0,
        )
        self.assertContains(
            response,
            "Please select a city",
        )

    @patch("garden_setup.views.get_location_by_id")
    def test_capacity_cannot_be_zero(self, mock_location):
        mock_location.return_value = self.location

        self.client.force_login(self.owner)

        data = self.data.copy()
        data["pot_capacity"] = "0"

        response = self.client.post(
            self.create_url,
            data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "pot_capacity",
            response.context["form"].errors,
        )
        self.assertEqual(
            GrowingSpace.objects.count(),
            0,
        )

    def test_edit_form_loads_existing_data(self):
        space = self.make_space()
        self.client.force_login(self.owner)

        url = reverse(
            "garden_setup:space_edit",
            args=[space.pk],
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Edit Growing Space",
        )
        self.assertContains(
            response,
            "My Balcony",
        )

    def test_edit_updates_existing_space(self):
        space = self.make_space()
        self.client.force_login(self.owner)

        url = reverse(
            "garden_setup:space_edit",
            args=[space.pk],
        )

        data = self.data.copy()
        data["name"] = "Updated Balcony"
        data["pot_capacity"] = "6"

        # Simulasikan hidden input yang dimanipulasi.
        data["latitude"] = "0"
        data["longitude"] = "0"

        response = self.client.post(url, data)

        self.assertRedirects(
            response,
            reverse("garden_setup:space_list"),
        )

        space.refresh_from_db()

        self.assertEqual(
            space.name,
            "Updated Balcony",
        )
        self.assertEqual(space.pot_capacity, 6)
        self.assertEqual(
            space.latitude,
            Decimal("-6.402500"),
        )
        self.assertEqual(space.user, self.owner)

    def test_cannot_edit_other_users_space(self):
        space = self.make_space(user=self.other)
        self.client.force_login(self.owner)

        url = reverse(
            "garden_setup:space_edit",
            args=[space.pk],
        )

        get_response = self.client.get(url)
        post_response = self.client.post(
            url,
            self.data,
        )

        self.assertEqual(get_response.status_code, 404)
        self.assertEqual(post_response.status_code, 404)

    def test_changed_city_requires_new_selection(self):
        space = self.make_space()
        self.client.force_login(self.owner)

        url = reverse(
            "garden_setup:space_edit",
            args=[space.pk],
        )

        data = self.data.copy()
        data["city"] = "Jakarta"

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)

        space.refresh_from_db()
        self.assertEqual(space.city, "Depok")

        self.assertContains(
            response,
            "Please select the new city",
        )

    @patch("garden_setup.views.search_locations")
    def test_location_search_returns_json(self, mock_search):
        mock_search.return_value = [self.location]

        self.client.force_login(self.owner)

        response = self.client.get(
            self.search_url,
            {"q": "Depok"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["results"][0]["name"],
            "Depok",
        )

    def test_location_search_requires_login(self):
        response = self.client.get(
            self.search_url,
            {"q": "Depok"},
        )

        self.assertEqual(response.status_code, 302)

    @patch("garden_setup.views.search_locations")
    def test_location_service_unavailable(self, mock_search):
        mock_search.side_effect = GeocodingServiceError(
            "Service unavailable"
        )

        self.client.force_login(self.owner)

        response = self.client.get(
            self.search_url,
            {"q": "Depok"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("error", response.json())

    @patch("garden_setup.views.get_location_by_id")
    def test_create_when_location_verification_fails(
        self,
        mock_location,
    ):
        mock_location.side_effect = GeocodingServiceError(
            "Service unavailable"
        )

        self.client.force_login(self.owner)

        response = self.client.post(
            self.create_url,
            self.data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            GrowingSpace.objects.count(),
            0,
        )
        self.assertContains(
            response,
            "Location service is unavailable",
        )