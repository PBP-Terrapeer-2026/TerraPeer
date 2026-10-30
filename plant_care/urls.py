from django.urls import path
from django.views.generic.base import RedirectView
from . import views

app_name = "care"
urlpatterns = [
    path(
        "home/",
        RedirectView.as_view(pattern_name="show_main", permanent=False),
        name="landing",
    ),
    path("", views.choose, name="choose"),
    path("link-previous-tasks/", views.link_legacy, name="link-legacy"),
    path("plants/<int:pk>/space/", views.set_space, name="set-space"),
    path("plants/<int:pk>/", views.page, name="page"),
    path("plants/<int:pk>/tasks/", views.task_list, name="list"),
    path("plants/<int:pk>/tasks/add/", views.add, name="add"),
    path("plants/<int:pk>/weather/", views.weather_view, name="weather"),
    path("tasks/<int:pk>/", views.detail, name="detail"),
    path("tasks/<int:pk>/edit/", views.edit, name="edit"),
    path("tasks/<int:pk>/complete/", views.complete, name="complete"),
    path("tasks/<int:pk>/undo/", views.undo, name="undo"),
    path("tasks/<int:pk>/delete/", views.delete, name="delete"),
]
