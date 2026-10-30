from django.db import models
from django.conf import settings
from django.utils import timezone

# Create your models here.

class GardenJournalEntry(models.Model):
    ENTRY_TYPE_CHOICES = [
        ("growth", "Growth"),
        ("flowering", "Flowering"),
        ("harvest", "Harvest"),
        ("issue", "Pest or Disease"),
        ("general", "Other"),
    ]

    # Pemilik catatan jurnal
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="garden_journal_entries",
    )
    #Nama tanaman sementara, hubungan dengan model My Plant
    plant_name = models.CharField(max_length=120)

    # Informasi utama jurnal
    entry_date = models.DateField(default=timezone.localdate)

    entry_type = models.CharField(
        max_length=20,
        choices=ENTRY_TYPE_CHOICES,
        default="growth",
    )

    title = models.CharField(max_length=120)
    notes = models.TextField()

    # Data tambahan, untuk catatan panen
    harvest_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    harvest_unit = models.CharField(
        max_length=30,
        blank=True,
    )

    # Ringkasan cuaca (opsional)
    weather_summary = models.CharField(
        max_length=200,
        blank=True,
    )

    # Waktu pencatatan dan pembaruan otomatis
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-entry_date", "-created_at"]

    def __str__(self):
        return (
            f"{self.plant_name} - "
            f"{self.get_entry_type_display()} "
            f"({self.entry_date})"
        )