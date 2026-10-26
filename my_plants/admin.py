from django.contrib import admin

from .models import Plant


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ['name', 'species_name', 'owner', 'growth_stage', 'planted_on']
    list_filter = ['growth_stage']
    search_fields = ['name', 'species_name', 'owner__username']
