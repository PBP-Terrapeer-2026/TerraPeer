from django.urls import path

from . import views

app_name = 'my_plants'

urlpatterns = [
    path('', views.plant_list, name='list'),
    path('add/', views.plant_create, name='create'),
    path('fragment/', views.plant_fragment, name='fragment'),
    path('api/', views.plant_api, name='api'),
    path('api/<int:pk>/', views.plant_detail_api, name='detail_api'),
    path('species/', views.species_api, name='species'),
    path('<int:pk>/', views.plant_detail, name='detail'),
    path('<int:pk>/edit/', views.plant_edit, name='edit'),
    path('<int:pk>/stage/', views.plant_stage, name='stage'),
    path('<int:pk>/delete/', views.plant_delete, name='delete'),
]
