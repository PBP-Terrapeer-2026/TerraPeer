from django.urls import path
from main.views import register, login_user, logout_user, show_main
from . import views

urlpatterns = [
    path("", show_main, name="show_main"),
    path("register/", register, name="register"),
    path("login/", login_user, name="login"),
    path("logout/", logout_user, name="logout"),
    path("garden-journal/", views.garden_journal, name="garden_journal",),
    path("garden-journal/add/", views.garden_journal_create, name="garden_journal_create",),
    path("garden-journal/<int:entry_id>/edit/", views.garden_journal_edit, name="garden_journal_edit",),
    path("garden-journal/<int:entry_id>/delete/", views.garden_journal_delete, name="garden_journal_delete",),
]
