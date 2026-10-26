from django.contrib import admin
from .models import GrowingSpace

@admin.register(GrowingSpace)
class GrowingSpaceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "city",
        "environment",
        "space_type",
        "pot_capacity",
        "created_at",
    )

    list_filter = (
        "environment",
        "space_type",
        "care_availability",
        "rain_access",
    )

    search_fields = (
        "name",
        "city",
        "user__username",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    list_select_related = ("user",)
    ordering = ("-created_at",)
    list_per_page = 20
