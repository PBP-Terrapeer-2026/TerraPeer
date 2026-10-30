"""Official-model fixtures shared by Plant Care regression tests."""

from garden_setup.models import GrowingSpace
from my_plants.models import Plant
from .models import PlantCareSpace


def make_space(user, **overrides):
    fields = dict(
        user=user,
        name="Balcony",
        environment="outdoor",
        space_type="balcony",
        geocoding_id=1642911,
        city="Depok",
        country="Indonesia",
        latitude=-6.4,
        longitude=106.8,
        timezone="Asia/Jakarta",
        sunlight_range="4-6",
        light_exposure="direct",
        growing_medium="soil",
        rain_access="exposed",
        support_available="yes",
        pot_capacity=4,
        care_availability="daily",
    )
    fields.update(overrides)
    return GrowingSpace.objects.create(**fields)


def make_plant(user, space=None, **overrides):
    fields = dict(owner=user, name="Mint", species_name="Peppermint")
    fields.update(overrides)
    plant = Plant.objects.create(**fields)
    if space:
        PlantCareSpace.objects.create(plant=plant, growing_space=space)
    return plant
