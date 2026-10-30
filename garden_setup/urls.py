from django.urls import path
from . import views

app_name = "garden_setup"

urlpatterns = [
    path("", views.space_list, name="space_list"),
    path("create/", views.space_create, name="space_create"),
    path("location-search/", views.location_search, name="location_search"),
    path("<int:pk>/", views.space_detail, name="space_detail"),
    path("<int:pk>/edit/", views.space_edit, name="space_edit"),
    path("<int:pk>/delete/", views.space_delete, name="space_delete"),
]