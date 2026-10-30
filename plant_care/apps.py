from django.apps import AppConfig


class PlantCareConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "plant_care"
    # Preserve existing database tables, migrations and permissions.
    label = "care"
    verbose_name = "Plant Care"
