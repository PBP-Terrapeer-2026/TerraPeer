from django.urls import path
from . import views

app_name = "garden_planning"

urlpatterns = [
    # Halaman utama garden planning
    path("", views.garden_planning_page, name="index"),

    # API: terima profil cuaca dari JS → kembalikan rekomendasi tanaman + pot
    path("api/recommend/", views.recommend_plants, name="recommend_plants"),
    path("api/pots/", views.pot_list_create, name="pot_list_create"),
    path("api/pots/<int:pk>/", views.pot_detail, name="pot_detail"),
    path("api/plants/", views.plant_create, name="plant_create"),

    # CRUD Plan
    path("api/plans/", views.plan_list_create, name="plan_list_create"),
    path("api/plans/<int:pk>/", views.plan_detail, name="plan_detail"),

    # CRUD PlanPlant (item dalam plan)
    path("api/plans/<int:plan_pk>/items/", views.planplant_list_create, name="planplant_list_create"),
    path("api/plans/<int:plan_pk>/items/<int:pk>/", views.planplant_detail, name="planplant_detail"),
]
