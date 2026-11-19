"""DRF API terpisah dari URL Django web lama."""
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from garden_setup.api import GrowingSpaceViewSet
from garden_planning.api import PlanViewSet
from my_plants.api import MyPlantViewSet
from plant_care.api import CareTaskViewSet
from main.api import JournalEntryViewSet

router = DefaultRouter()
router.register(r"spaces", GrowingSpaceViewSet, basename="api-spaces")
router.register(r"plans", PlanViewSet, basename="api-plans")
router.register(r"my-plants", MyPlantViewSet, basename="api-my-plants")
router.register(r"care-tasks", CareTaskViewSet, basename="api-care-tasks")
router.register(r"journal-entries", JournalEntryViewSet, basename="api-journal")

urlpatterns = [
    path("auth/token/", obtain_auth_token, name="api-token"),
    path("", include(router.urls)),
]
