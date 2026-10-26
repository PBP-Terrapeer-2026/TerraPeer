from django.shortcuts import render
from django.http import HttpResponse
import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET

PERENUAL= "https://perenual.com/api/v2/species-list?key="

@require_GET
def get_or_cache_plant(perenual_id):
    plant = Plant.objects.filter(perenual_id=perenual_id).first()
    if plant:
        return plant

# Create your views here.
