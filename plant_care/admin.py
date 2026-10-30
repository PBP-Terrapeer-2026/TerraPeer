from django.contrib import admin
from .models import CareTask, PlantCareSpace

admin.site.register([CareTask, PlantCareSpace])
