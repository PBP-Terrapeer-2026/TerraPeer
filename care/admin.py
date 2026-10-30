from django.contrib import admin
from .models import GardenSpace, Plant, CareTask

admin.site.register([GardenSpace, Plant, CareTask])
