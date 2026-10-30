"""Official plants for new tasks; archived adapters preserve pre-integration data."""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


class LegacyGardenSpace(models.Model):
    class Meta:
        db_table = "care_gardenspace"
        verbose_name = "Archived care space"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=150, default="Depok")
    latitude = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    timezone_name = models.CharField(max_length=80, default="Asia/Jakarta")

    def clean(self):
        try:
            ZoneInfo(self.timezone_name)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValidationError(
                {"timezone_name": "Use an IANA timezone, e.g. Asia/Jakarta."}
            )

    def __str__(self):
        return self.name


class LegacyPlant(models.Model):
    class Meta:
        db_table = "care_plant"
        verbose_name = "Archived care plant"

    garden = models.ForeignKey(
        LegacyGardenSpace, on_delete=models.CASCADE, related_name="plants"
    )
    name = models.CharField(max_length=100)
    pot = models.CharField(max_length=50)
    status = models.CharField(
        max_length=12,
        choices=[
            ("Active", "Active"),
            ("Finished", "Finished"),
            ("Failed", "Failed"),
            ("Removed", "Removed"),
        ],
        default="Active",
    )
    image = models.CharField(
        max_length=10, choices=[("mint", "Mint"), ("tomato", "Tomato")], default="mint"
    )

    @property
    def active(self):
        return self.status == "Active"

    @property
    def image_path(self):
        return "terrapeer/img/" + self.image + ".png"

    @property
    def today(self):
        return timezone.localdate(timezone=ZoneInfo(self.garden.timezone_name))

    def __str__(self):
        return self.name


class CareTask(models.Model):

    ACTIONS = [
        ("Watering", "Watering"),
        ("Fertilizing", "Fertilizing"),
        ("Pruning", "Pruning"),
        ("Inspection", "Inspection"),
        ("Repotting", "Repotting"),
    ]
    plant = models.ForeignKey(
        "my_plants.Plant",
        on_delete=models.PROTECT,
        related_name="care_tasks",
        null=True,
        blank=True,
    )
    # Only populated for tasks created before the My Plants integration.
    legacy_plant = models.ForeignKey(
        LegacyPlant,
        on_delete=models.PROTECT,
        related_name="care_tasks",
        null=True,
        blank=True,
        editable=False,
    )
    title = models.CharField(max_length=160)
    action_type = models.CharField(max_length=20, choices=ACTIONS)
    due_date = models.DateField()
    repeat_every = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1)]
    )
    instructions = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=[("Pending", "Pending"), ("Completed", "Completed")],
        default="Pending",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    # Unique: satu tugas sumber hanya boleh punya satu penerus. Hapus riwayat tidak menghapus penerus.
    previous = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="next_task",
    )

    class Meta:
        ordering = ["due_date", "pk"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(plant__isnull=False)
                | models.Q(legacy_plant__isnull=False),
                name="care_task_has_plant",
            ),
            models.CheckConstraint(
                condition=models.Q(repeat_every__isnull=True)
                | models.Q(repeat_every__gte=1),
                name="care_repeat_positive",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status="Pending", completed_at__isnull=True)
                    | models.Q(status="Completed", completed_at__isnull=False)
                ),
                name="care_completion_consistent",
            ),
        ]

    @property
    def overdue(self):
        from .integration import plant_today

        today = plant_today(self.plant) if self.plant_id else self.legacy_plant.today
        return self.status == "Pending" and self.due_date < today

    @property
    def repeat_label(self):
        if self.repeat_every == 1:
            return "Every day"
        return (
            f"Every {self.repeat_every} days"
            if self.repeat_every
            else "Does not repeat"
        )

    def __str__(self):
        return self.title


class PlantCareSpace(models.Model):
    """Care's weather location; references official records without copying them."""

    plant = models.OneToOneField(
        "my_plants.Plant",
        on_delete=models.CASCADE,
        related_name="care_location",
    )
    growing_space = models.ForeignKey(
        "garden_setup.GrowingSpace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="care_locations",
    )

    def clean(self):
        super().clean()
        if self.plant_id and self.growing_space_id:
            if self.plant.owner_id != self.growing_space.user_id:
                raise ValidationError(
                    {"growing_space": "Choose a space owned by the plant owner."}
                )

    def __str__(self):
        return f"Care location · {self.plant}"
