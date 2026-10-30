from django.urls import path
from . import views
from garden_planning.views import garden_planning_page, plan_summary_page, city_suggestions, recommend_plants, pot_list_create, pot_list_partial, pot_detail, plant_create, plan_list_create, plan_detail, planplant_list_create, planplant_detail

app_name = "garden_planning"

urlpatterns = [
    # Halaman utama garden planning
    path("", garden_planning_page, name="index"),
    path("plans/<int:pk>/", plan_summary_page, name="plan_summary"),
    path("api/city-suggestions/", city_suggestions, name="city_suggestions"),

    # API: terima profil cuaca dari JS → kembalikan rekomendasi tanaman + pot
    path("api/recommend/", recommend_plants, name="recommend_plants"),
    path("api/pots/", pot_list_create, name="pot_list_create"),
    path("partials/pots/", pot_list_partial, name="pot_list_partial"),
    path("api/pots/<int:pk>/", pot_detail, name="pot_detail"),
    path("api/plants/", plant_create, name="plant_create"),

    # CRUD Plan
    path("api/plans/", plan_list_create, name="plan_list_create"),
    path("api/plans/<int:pk>/", plan_detail, name="plan_detail"),

    # CRUD PlanPlant (item dalam plan)
    path("api/plans/<int:plan_pk>/items/", planplant_list_create, name="planplant_list_create"),
    path("api/plans/<int:plan_pk>/items/<int:pk>/", planplant_detail, name="planplant_detail"),
]
