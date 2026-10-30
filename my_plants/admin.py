from django.contrib import admin

from .models import Plant, PlantCheckIn, PlantPhoto


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ['name', 'species_name', 'owner', 'growth_stage', 'planted_on']
    list_filter = ['growth_stage']
    search_fields = ['name', 'species_name', 'owner__username']

@admin.register(PlantCheckIn)
class PlantCheckInAdmin(admin.ModelAdmin):
    list_display = ['plant', 'condition', 'created_at']
    list_filter = ['condition']

@admin.register(PlantPhoto)
class PlantPhotoAdmin(admin.ModelAdmin):
    list_display = ['plant', 'stage', 'kind', 'width', 'height', 'created_at']
    list_filter = ['stage', 'kind']
    exclude = ['image']
