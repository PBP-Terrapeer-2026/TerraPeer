from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    MinLengthValidator,
    MinValueValidator,
    MaxValueValidator,
)
from django.db import models

class GrowingSpace(models.Model):

    # CHOICE DEFINITIONS
    class Environment(models.TextChoices):
        INDOOR = "indoor", "Indoor"
        OUTDOOR = "outdoor", "Outdoor"

    class SpaceType(models.TextChoices):
        BALCONY = "balcony", "Balcony"
        YARD = "yard", "Yard"
        ROOFTOP = "rooftop", "Rooftop"
        ROOM = "room", "Room"
        OTHER = "other", "Other"

    class SunlightRange(models.TextChoices):
        HOURS_0_2 = "0-2", "0–2 hours/day"
        HOURS_2_4 = "2-4", "2–4 hours/day"
        HOURS_4_6 = "4-6", "4–6 hours/day"
        HOURS_6_8 = "6-8", "6–8 hours/day"
        HOURS_8_PLUS = "8+", "8+ hours/day"

    class LightExposure(models.TextChoices):
        DIRECT = "direct", "Direct"
        INDIRECT = "indirect", "Indirect"
        MIXED = "mixed", "Mixed"

    class GrowingMedium(models.TextChoices):
        SOIL = "soil", "Soil"
        HYDROPONIC = "hydroponic", "Hydroponic"
        OTHER = "other", "Other"

    class RainAccess(models.TextChoices):
        EXPOSED = "exposed", "Exposed"
        SHELTERED = "sheltered", "Sheltered"

    class SupportAvailability(models.TextChoices):
        YES = "yes", "Yes"
        NO = "no", "No"

    class CareAvailability(models.TextChoices):
        DAILY = "daily", "Daily"
        SEVERAL = "several", "Several times a week"
        WEEKLY = "weekly", "Weekly"

    # OWNERSHIP
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="growing_spaces",
    )

    # BASIC INFORMATION
    name = models.CharField(
        max_length=60,
        validators=[MinLengthValidator(2)],
    )

    environment = models.CharField(
        max_length=10,
        choices=Environment.choices,
    )

    space_type = models.CharField(
        max_length=20,
        choices=SpaceType.choices,
    )

    # LOCATION
    geocoding_id = models.PositiveBigIntegerField()

    city = models.CharField(max_length=120)

    region = models.CharField(
        max_length=120,
        blank=True,
    )

    country = models.CharField(max_length=120)

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(Decimal("-90")),
            MaxValueValidator(Decimal("90")),
        ],
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(Decimal("-180")),
            MaxValueValidator(Decimal("180")),
        ],
    )

    timezone = models.CharField(max_length=64)

    # GROWING CONDITIONS
    sunlight_range = models.CharField(
        max_length=10,
        choices=SunlightRange.choices,
    )

    light_exposure = models.CharField(
        max_length=10,
        choices=LightExposure.choices,
    )

    growing_medium = models.CharField(
        max_length=20,
        choices=GrowingMedium.choices,
    )

    rain_access = models.CharField(
        max_length=15,
        choices=RainAccess.choices,
    )

    support_available = models.CharField(
        max_length=3,
        choices=SupportAvailability.choices,
    )

    # CAPACITY & CARE
    pot_capacity = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(100),
        ],
    )

    care_availability = models.CharField(
        max_length=10,
        choices=CareAvailability.choices,
    )

    # ADDITIONAL INFORMATION
    notes = models.TextField(
        max_length=500,
        blank=True,
    )

    # TIMESTAMPS
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # MODEL VALIDATION
    def clean(self):
        super().clean()

        if (
            self.environment == self.Environment.INDOOR
            and self.rain_access == self.RainAccess.EXPOSED
        ):
            raise ValidationError({
                "rain_access": (
                    "Indoor spaces must have sheltered rain access."
                )
            })

    # MODEL METADATA
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Growing Space"
        verbose_name_plural = "Growing Spaces"

    def __str__(self):
        return f"{self.name} ({self.user})"

