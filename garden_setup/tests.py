from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from .forms import GrowingSpaceForm
from .models import GrowingSpace

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