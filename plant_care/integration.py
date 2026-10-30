"""Read official module records without changing their fields or workflows."""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from my_plants.models import Plant


def plants_for(user):
    return Plant.objects.for_user(user).select_related("care_location__growing_space")


def plant_space(plant):
    try:
        space = plant.care_location.growing_space
    except ObjectDoesNotExist:
        return None
    # Protect reads even if invalid data was inserted outside the form.
    return space if space and space.user_id == plant.owner_id else None


def plant_timezone(plant):
    space = plant_space(plant)
    try:
        return ZoneInfo(space.timezone) if space else timezone.get_default_timezone()
    except (ZoneInfoNotFoundError, ValueError):
        return timezone.get_default_timezone()


def plant_today(plant):
    return timezone.localdate(timezone=plant_timezone(plant))
