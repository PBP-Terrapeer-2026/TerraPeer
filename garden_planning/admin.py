from django.contrib import admin

# Register your models here.


class Plant(models.Model):
    # perenual_id kosong jika tanaman diinput manual oleh pengguna
    perenual_id = models.PositiveIntegerField(null=True, blank=True, unique=True)
    name = models.CharField(max_length=150)
    watering = models.CharField(max_length=30, blank=True)
    sunlight = models.JSONField(default=list, blank=True)
    benefit = models.CharField(max_length=200, blank=True)  # hias, konsumsi, obat
    image_url = models.URLField(blank=True)

    def __str__(self):
        return self.name


class Pot(models.Model):
    name = models.CharField(max_length=100)
    size_cm = models.PositiveIntegerField()
    material = models.CharField(max_length=50, blank=True)
    drainage = models.BooleanField(default=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.CASCADE)

class Plan(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    location_name = models.CharField(max_length=150, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    environment_profile = models.JSONField(default=dict, blank=True)  # hasil buildProfile
    created_at = models.DateTimeField(auto_now_add=True)
    is_draft = models.BooleanField(default=True) 

    def __str__(self):
        return self.name

class PlanPlant(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="items")
    plant = models.ForeignKey(Plant, on_delete=models.PROTECT)
    pot = models.ForeignKey(Pot, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    note = models.CharField(max_length=200, blank=True)