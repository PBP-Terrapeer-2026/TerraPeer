from django.urls import path
from . import views

app_name = "garden_setup"

urlpatterns = [
    path("", views.space_list, name="space_list"),
]