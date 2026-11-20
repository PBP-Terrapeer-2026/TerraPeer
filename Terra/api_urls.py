"""DRF API terpisah dari URL Django web lama."""
from django.urls import include, path, re_path
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.routers import DefaultRouter
from rest_framework.throttling import ScopedRateThrottle

from garden_setup.api import GrowingSpaceViewSet
from garden_planning.api import PlanViewSet
from my_plants.api import MyPlantViewSet
from plant_care.api import CareTaskViewSet
from main.api import JournalEntryViewSet

from .api_exceptions import api_not_found


@extend_schema(tags=["auth"], summary="Log in and get an API token")
class LoginView(ObtainAuthToken):
    """POST username + password, returns {"token": "..."}. Limited to 10 tries per minute."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


router = DefaultRouter()
router.register(r"spaces", GrowingSpaceViewSet, basename="api-spaces")
router.register(r"plans", PlanViewSet, basename="api-plans")
router.register(r"my-plants", MyPlantViewSet, basename="api-my-plants")
router.register(r"care-tasks", CareTaskViewSet, basename="api-care-tasks")
router.register(r"journal-entries", JournalEntryViewSet, basename="api-journal")

urlpatterns = [
    path("auth/token/", LoginView.as_view(), name="api-token"),
    # Automatic API documentation (OpenAPI 3).
    path("schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
    path("redoc/", SpectacularRedocView.as_view(url_name="api-schema"), name="api-redoc"),
    path("", include(router.urls)),
    # Unknown API paths answer with JSON, not the HTML 404 page. Only paths
    # ending in "/" so APPEND_SLASH still redirects "/api/v1/my-plants".
    re_path(r"^.*/$", api_not_found),
]
