from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class PlantQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(owner=user)

    def active(self):
        return self.exclude(growth_stage=Plant.Stage.FINISHED)


class Plant(models.Model):
    class Stage(models.TextChoices):
        GROWING = 'growing', 'Growing'
        FLOWERING = 'flowering', 'Flowering'
        FRUITING = 'fruiting', 'Fruiting'
        HARVESTING = 'harvesting', 'Harvesting'
        FINISHED = 'finished', 'Finished'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='plants',
    )
    name = models.CharField(max_length=120)
    species_name = models.CharField(max_length=160)
    planted_on = models.DateField(default=timezone.localdate)
    growth_stage = models.CharField(
        max_length=20, choices=Stage.choices, default=Stage.GROWING,
    )
    notes = models.TextField(blank=True, max_length=2000)
    perenual_species_id = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PlantQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at', '-pk']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(growth_stage__in=[
                    'growing', 'flowering', 'fruiting', 'harvesting', 'finished',
                ]),
                name='my_plants_valid_stage',
            ),
        ]

    @property
    def status(self):
        # Derived so a Finished plant can never also be Active.
        return 'finished' if self.growth_stage == self.Stage.FINISHED else 'active'

    @property
    def days_growing(self):
        return max(0, (timezone.localdate() - self.planted_on).days)

    def clean(self):
        super().clean()
        if self.planted_on and self.planted_on > timezone.localdate():
            raise ValidationError({'planted_on': 'The planting date cannot be in the future.'})

    def get_absolute_url(self):
        return reverse('my_plants:detail', args=[self.pk])

    def __str__(self):
        return self.name

class PlantCheckIn(models.Model):
    """A quick, one-tap record of how a plant looks today (README: "pilih opsi kondisi tanaman")."""

    class Condition(models.TextChoices):
        NORMAL = 'normal', 'Growing normally'
        WILTING = 'wilting', 'Wilting'
        YELLOW_LEAVES = 'yellow_leaves', 'Yellow leaves'
        PESTS = 'pests', 'Pests spotted'
        DRY_SOIL = 'dry_soil', 'Dry soil'
        OVERWATERED = 'overwatered', 'Overwatered'

    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name='check_ins')
    condition = models.CharField(max_length=20, choices=Condition.choices)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']

    @property
    def needs_attention(self):
        return self.condition != self.Condition.NORMAL

    def __str__(self):
        return f'{self.plant} · {self.get_condition_display()}'

class PlantPhotoQuerySet(models.QuerySet):
    def without_image(self):
        """Lists never need the binary data; load it only when a photo is served."""
        return self.defer('image')


class PlantPhoto(models.Model):
    """A photo of a plant, stored in the database so it survives redeploys on PWS."""

    class Kind(models.TextChoices):
        START = 'start', 'First photo'
        STAGE = 'stage', 'Stage update'
        PROGRESS = 'progress', 'Progress photo'

    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name='photos')
    image = models.BinaryField()
    content_type = models.CharField(max_length=30, default='image/jpeg')
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    stage = models.CharField(max_length=20, choices=Plant.Stage.choices)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.PROGRESS)
    caption = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = PlantPhotoQuerySet.as_manager()

    class Meta:
        ordering = ['created_at', 'pk']

    def get_absolute_url(self):
        return reverse('my_plants:photo', args=[self.plant_id, self.pk])

    @property
    def day_number(self):
        """Day N of the plant's life when the photo was taken (planting day = day 0)."""
        return max(0, (timezone.localtime(self.created_at).date() - self.plant.planted_on).days)

    def __str__(self):
        return f'{self.plant} · {self.get_stage_display()} · {self.created_at:%Y-%m-%d}'
