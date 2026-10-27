from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings

import requests
import json
import random
import math
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from .models import Plant, Pot, Plan, PlanPlant



PERENUAL_BASE = "https://perenual.com/api/v2/species-list"


POTS = [
    {"name": "Pot kecil terakota",  "size_cm": 15, "material": "terakota"},
    {"name": "Pot sedang plastik",  "size_cm": 30, "material": "plastik"},
    {"name": "Pot besar glazed",    "size_cm": 45, "material": "keramik glazed"},
    {"name": "Planter box",         "size_cm": 60, "material": "kayu/plastik"},
]
POT_MATERIAL_CHOICES = {"plastik", "terakota", "keramik glazed", "kayu/plastik"}
LOCATION_MATCH_TOLERANCE = 0.01  # sekitar 1 km, untuk toleransi koordinat titik kota


def build_perenual_filters(profile) -> dict: #input berupa dict
    """
    Mengonversi profil cuaca (dari Open-Meteo geocoding) menjadi filter query (q) Perenual.

    profile keys yang diharapkan didapat:
      - avg_rain_mm   : rata-rata curah hujan harian (mm)
      - avg_temp_c    : rata-rata suhu harian (°C)
      - avg_radiation : rata-rata radiasi gelombang pendek (MJ/m²)
      - avg_humidity  : rata-rata kelembapan relatif (%)

    Returns dict dengan key 'watering' dan/atau 'sunlight'. --->tipe kelembaban 
    """
    filters = {}

    rain    = profile.get("avg_rain_mm", 0)
    temp    = profile.get("avg_temp_c", 25)
    rad     = profile.get("avg_radiation", 10)
    humidity = profile.get("avg_humidity", 60)

    
    if rain >= 5 or humidity >= 80:
        filters["watering"] = "minimum"

    elif rain >= 1:
        filters["watering"] = "average"
 
    else:
        filters["watering"] = "frequent"

    if rad >= 15:
        filters["sunlight"] = "full_sun"
    elif rad >= 8:
        filters["sunlight"] = "part_sun"
    else:
        filters["sunlight"] = "part_shade"

    return filters



def recommend_pot(profile: dict) -> dict:
    """
    Memilih pot yang paling sesuai dari POTS berdasarkan profil cuaca. (pilihan pot disini hardcode karena tidak terdapat di perenual)
      - Hujan deras / outdoor: pot besar dengan drainase baik (terakota/kayu)
      - Dalam ruangan / teduh: pot sedang plastik
      - Umum: pot sedang
    """
    rain = profile.get("avg_rain_mm", 0)
    rad  = profile.get("avg_radiation", 10)

    if rad < 8:         
        return POTS[1]   
    elif rain >= 5:      
        return POTS[0]   
    elif rad >= 15:     
        return POTS[3]   
    else:
        return POTS[2]   #default



def fetch_plants_from_perenual(watering, sunlight, page = 1) : #watering str sunlight str page int
  """
  melakukan fetching perenual API, dilakuakn di back-end karena mengandung api key yang mana jika 
  dilakukan di front-end/client side maka proses yang mengandung key rahasia ini akan terikirim ke web.
  Disini juga url akan dipecah menjadi dict  
  """
  configured_url = (getattr(settings, "API_URL", "") or "").strip() #getattr from django docs
  api_key = (getattr(settings, "PERENUAL_API_KEY", "") or "").strip()
  if not configured_url and not api_key:
    return []

  # Handle pemanggilan API URL dengan variabel cadangan.
  target = configured_url or PERENUAL_BASE
  parsed = urlparse(target)
  query = dict(parse_qsl(parsed.query, keep_blank_values=True))
  if query.get("key"):
      query["key"] = query["key"].strip()
  if api_key and not query.get("key"):
      query["key"] = api_key
  query.update({"watering": watering, "sunlight": sunlight, "page": page})
  target = urlunparse(parsed._replace(query=urlencode(query)))
  try:
      resp = requests.get(target, timeout=10)
      resp.raise_for_status()
      data = resp.json()
      if isinstance(data, dict):
          return data.get("data", [])
      return []
  except Exception as exc:
      # Jangan mencetak detail exception: URL request dapat memuat API key.
      print(f"[Perenual] Request failed: {type(exc).__name__}")
      return []


def fetch_plant_details_from_perenual(perenual_id):
    """Ambil data detail tanaman, termasuk description yang tidak konsisten ada di species-list."""
    configured_url = (getattr(settings, "API_URL", "") or "").strip()
    api_key = (getattr(settings, "PERENUAL_API_KEY", "") or "").strip()
    parsed = urlparse(configured_url or PERENUAL_BASE)
    path = parsed.path
    if "/species-list" in path:
        path = path.split("/species-list", 1)[0] + f"/species/details/{perenual_id}"
    else:
        path = f"/api/v2/species/details/{perenual_id}"

    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    key = api_key or query.get("key", "").strip()
    if not key:
        return {}
    try:
        response = requests.get(
            urlunparse(parsed._replace(path=path, query=urlencode({"key": key}))),
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        # Jangan mencetak URL karena query memuat API key.
        print(f"[Perenual] Detail request failed: {type(exc).__name__}")
        return {}


def first_description_sentence(description):
    """Batasi deskripsi yang ditampilkan ke kalimat pertama."""
    description = (description or "").strip()
    if not description:
        return ""
    first_sentence = description.split(".", 1)[0].strip()
    return f"{first_sentence}." if first_sentence else ""


def get_or_cache_plant(Pdata) : #param=dictionary
    """
    Simpan atau ambil tanaman dari DB lokal (cache) berdasarkan perenual_id.
    """
    perenual_id = Pdata.get("id")
    plant, _ = Plant.objects.get_or_create(
        perenual_id=perenual_id,
        defaults={
            "name":      Pdata.get("common_name") or Pdata.get("scientific_name", [""])[0],
            "watering":  Pdata.get("watering", ""),
            "sunlight":  Pdata.get("sunlight", []),
            "description": Pdata.get("description", ""),
            "image_url": (Pdata.get("default_image") or {}).get("medium_url", ""),
        },
    )
    # Isi juga cache lama yang dibuat sebelum deskripsi Perenual disimpan.
    description = Pdata.get("description", "")
    if description and plant.description != description:
        plant.description = description
        plant.save(update_fields=["description"])
    return plant


##main views
@login_required
def garden_planning_page(request):
    """Render halaman utama Garden Planning."""
    plans = Plan.objects.filter(owner=request.user).order_by("-created_at")
    return render(request, "garden_planning_template/index.html", {"plans": plans})


@login_required
def plan_summary_page(request, pk):
    """Render halaman ringkasan terpisah untuk satu plan milik pengguna."""
    plan = get_object_or_404(Plan, pk=pk, owner=request.user)
    items = list(plan.items.select_related("plant", "pot").all())
    for item in items:
        item.description_preview = first_description_sentence(item.plant.description or item.plant.benefit)

    recommended_pot = recommend_pot(plan.environment_profile or {})
    matching_pots = Pot.objects.filter(
        owner=request.user,
        material__iexact=recommended_pot["material"],
        size_cm__gte=recommended_pot["size_cm"],
    ).count()
    total_quantity = sum(item.quantity for item in items)
    return render(request, "garden_planning_template/plan_summary.html", {
        "plan": plan,
        "items": items,
        "pots": Pot.objects.filter(owner=request.user).order_by("name"),
        "recommended_pot": recommended_pot,
        "recommended_filters": build_perenual_filters(plan.environment_profile or {}),
        "matching_pots": matching_pots,
        "total_quantity": total_quantity,
        "pots_needed": max(0, total_quantity - matching_pots),
        "status_choices": Plan.STATUS_CHOICES,
    })


@login_required
@require_GET
def city_suggestions(request):
    """Kembalikan tiga saran kota untuk autocomplete HTMX."""
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return render(request, "garden_planning_template/_city_suggestions.html", {"cities": []})

    try:
        response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": query, "count": 3, "language": "id", "format": "json"},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        cities = data.get("results", []) if isinstance(data, dict) else []
    except (requests.RequestException, ValueError):
        cities = []

    return render(request, "garden_planning_template/_city_suggestions.html", {"cities": cities[:3]})


@login_required
@require_POST
def recommend_plants(request):
    """
    POST /garden_planning/api/recommend/
    Body JSON: profil cuaca dari Open-Meteo yang sudah dihitung di JS.

    {
        "avg_rain_mm":   3.2,
        "avg_temp_c":    28.5,
        "avg_radiation": 18.0,
        "avg_humidity":  72.0
    }

    Response:
    {
        "filters":  { "watering": "...", "sunlight": "..." },
        "plants":   [ { id, name, watering, sunlight, image_url } … ],
        "pot":      { name, size_cm, material }
    }
    """
    try:
        profile = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Body bukan JSON valid."}, status=400)


    filters = build_perenual_filters(profile)

   
    pot = recommend_pot(profile)

   #disini akan dirandom untuk rekomendasi tanaman agar lebih bervariasi 
    raw_plants = []
    seen_ids = set()
    for page in range(1, 4):
        page_plants = fetch_plants_from_perenual(
            watering=filters["watering"],
            sunlight=filters["sunlight"],
            page=page,
        ) or []
        for candidate in page_plants:
            candidate_id = candidate.get("id")
            if candidate_id not in seen_ids:
                seen_ids.add(candidate_id)
                raw_plants.append(candidate)
    random.shuffle(raw_plants)

    # 4. Cache ke DB & bentuk response
    result_plants = []
    for p in raw_plants[:10]:   # pilih maksimal 10 kandidat secara acak
        plant = get_or_cache_plant(p)
        description = first_description_sentence(p.get("description") or plant.description)
        if not description and plant.perenual_id:
            details = fetch_plant_details_from_perenual(plant.perenual_id)
            full_description = details.get("description", "")
            description = first_description_sentence(full_description)
            if full_description:
                plant.description = full_description
                plant.save(update_fields=["description"])
        result_plants.append({
            "id":        plant.pk,
            "name":      plant.name,
            "watering":  plant.watering,
            "sunlight":  plant.sunlight,
            "description": description or "Deskripsi tanaman belum tersedia.",
            "image_url": plant.image_url,
        })

    if not result_plants:
        cached = list(Plant.objects.filter(perenual_id__isnull=True).order_by("name")[:10])
        #membuat asumsi menggunakan data hard code
        if not cached:
            suggestions = [
                ("Kemangi", "average", ["part_sun", "full_sun"], "Bumbu dapur dan menarik penyerbuk"),
                ("Cabai", "average", ["full_sun"], "Bahan pangan dan bumbu dapur"),
                ("Lidah mertua", "minimum", ["part_sun", "part_shade"], "Tanaman hias yang tahan kering"),
                ("Kangkung", "frequent", ["full_sun", "part_sun"], "Sayuran daun untuk konsumsi"),
            ]
            cached = [Plant.objects.get_or_create(name=name, perenual_id=None,
                defaults={"watering": water, "sunlight": sun, "benefit": benefit})[0]
                for name, water, sun, benefit in suggestions]
        result_plants = [{"id": p.pk, "name": p.name, "watering": p.watering,
            "sunlight": p.sunlight, "description": first_description_sentence(p.description or p.benefit) or "Deskripsi tanaman belum tersedia.",
            "image_url": p.image_url} for p in cached]
        random.shuffle(result_plants)

    return JsonResponse({
        "filters": filters,
        "plants":  result_plants,
        "pot":     pot,
    })



@login_required
@require_http_methods(["GET", "POST"])
def pot_list_create(request):
    if request.method == "GET":
        pots = Pot.objects.filter(owner=request.user)
        return JsonResponse({"pots": [{"id": p.pk, "name": p.name, "size_cm": p.size_cm,
            "material": p.material, "drainage": p.drainage} for p in pots]})
    try:
        body = json.loads(request.body)
        name, size = str(body.get("name", "")).strip(), int(body.get("size_cm", 0))
        material = str(body.get("material", "")).strip()
        if not name or size < 1 or material not in POT_MATERIAL_CHOICES: raise ValueError
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({"error": "Nama, ukuran pot, dan bahan pot yang valid wajib diisi."}, status=400)
    pot = Pot.objects.create(owner=request.user, name=name, size_cm=size,
        material=material, drainage=bool(body.get("drainage", True)))
    return JsonResponse({"id": pot.pk, "name": pot.name, "size_cm": pot.size_cm,
        "material": pot.material, "drainage": pot.drainage}, status=201)


@login_required
@require_http_methods(["PUT", "DELETE"])
def pot_detail(request, pk):
    pot = get_object_or_404(Pot, pk=pk, owner=request.user)
    if request.method == "DELETE":
        pot.delete()
        return JsonResponse({"ok": True})
    try:
        body = json.loads(request.body)
        if "name" in body: pot.name = str(body["name"]).strip()
        if "size_cm" in body: pot.size_cm = int(body["size_cm"])
        if "material" in body: pot.material = str(body["material"]).strip()
        if "drainage" in body: pot.drainage = bool(body["drainage"])
        if not pot.name or pot.size_cm < 1: raise ValueError
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({"error": "Data pot tidak valid."}, status=400)
    pot.save()
    return JsonResponse({"ok": True})


@login_required
@require_POST
def plant_create(request):
    try:
        body = json.loads(request.body)
        name = str(body.get("name", "")).strip()
        if not name: raise ValueError
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({"error": "Nama tanaman wajib diisi."}, status=400)
    plant = Plant.objects.create(name=name, benefit=str(body.get("benefit", "")).strip(),
        watering=str(body.get("watering", "")).strip(), sunlight=body.get("sunlight", []))
    return JsonResponse({"id": plant.pk, "name": plant.name, "benefit": plant.benefit}, status=201)



@login_required
@require_http_methods(["GET", "POST"])
def plan_list_create(request):
    if request.method == "GET":
        plans = Plan.objects.filter(owner=request.user).order_by("-created_at")
        data = [
            {
                "id":           p.pk,
                "name":         p.name,
                "status":       p.status,
                "location_name": p.location_name,
                "latitude":     p.latitude,
                "longitude":    p.longitude,
                "is_draft":     p.is_draft,
                "created_at":   p.created_at.isoformat(),
            }
            for p in plans
        ]
        return JsonResponse({"plans": data})


    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "JSON tidak valid."}, status=400)

    plan = Plan.objects.create(
        owner               = request.user,
        name                = body.get("name", "Rencana Baru"),
        location_name       = body.get("location_name", ""),
        latitude            = body.get("latitude", 0),
        longitude           = body.get("longitude", 0),
        environment_profile = body.get("environment_profile", {}),
        is_draft            = body.get("is_draft", True),
    )
    return JsonResponse({"id": plan.pk, "name": plan.name, "status": plan.status}, status=201)


@login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def plan_detail(request, pk):
    plan = get_object_or_404(Plan, pk=pk, owner=request.user)

    if request.method == "GET":
        items = [
            {
                "id":       item.pk,
                "plant_id": item.plant.pk,
                "plant":    item.plant.name,
                "image":    item.plant.image_url,
                "pot":      item.pot.name if item.pot else None,
                "pot_id":   item.pot_id,
                "quantity": item.quantity,
                "note":     item.note,
            }
            for item in plan.items.select_related("plant", "pot").all()
        ]
        recommended_pot = recommend_pot(plan.environment_profile or {})
        matching_pots = Pot.objects.filter(
            owner=request.user,
            material__iexact=recommended_pot["material"],
            size_cm__gte=recommended_pot["size_cm"],
        ).count()
        return JsonResponse({
            "id":           plan.pk,
            "name":         plan.name,
            "status":       plan.status,
            "location_name": plan.location_name,
            "latitude":     plan.latitude,
            "longitude":    plan.longitude,
            "environment_profile": plan.environment_profile,
            "is_draft":     plan.is_draft,
            "items":        items,
            "recommended_pot": recommended_pot,
            "matching_pots": matching_pots,
        })

    if request.method == "PUT":
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "JSON tidak valid."}, status=400)

        plan.name                = body.get("name", plan.name)
        plan.location_name       = body.get("location_name", plan.location_name)
        plan.latitude            = body.get("latitude", plan.latitude)
        plan.longitude           = body.get("longitude", plan.longitude)
        plan.environment_profile = body.get("environment_profile", plan.environment_profile)
        plan.is_draft            = body.get("is_draft", plan.is_draft)
        if "status" in body:
            if not isinstance(body["status"], str) or body["status"] not in dict(Plan.STATUS_CHOICES):
                return JsonResponse({"error": "Status plan tidak valid."}, status=400)
            plan.status = body["status"]
        plan.save()
        return JsonResponse({"ok": True})

    # DELETE
    plan.delete()
    return JsonResponse({"ok": True})


#CRUD session

@login_required
@require_http_methods(["GET", "POST"])
def planplant_list_create(request, plan_pk):
    plan = get_object_or_404(Plan, pk=plan_pk, owner=request.user)

    if request.method == "GET":
        items = [
            {
                "id":       item.pk,
                "plant_id": item.plant.pk,
                "plant":    item.plant.name,
                "image":    item.plant.image_url,
                "pot":      item.pot.name if item.pot else None,
                "pot_id":   item.pot.pk   if item.pot else None,
                "quantity": item.quantity,
                "note":     item.note,
            }
            for item in plan.items.select_related("plant", "pot").all()
        ]
        return JsonResponse({"items": items})
#tambah
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "JSON tidak valid."}, status=400)

    try:
        recommendation_latitude = float(body["recommendation_latitude"])
        recommendation_longitude = float(body["recommendation_longitude"])
    except (KeyError, TypeError, ValueError):
        return JsonResponse({"error": "Lokasi rekomendasi wajib dipilih sebelum menambahkan tanaman."}, status=400)

    if not math.isfinite(recommendation_latitude) or not math.isfinite(recommendation_longitude):
        return JsonResponse({"error": "Koordinat lokasi rekomendasi tidak valid."}, status=400)
    same_location = (
        math.isclose(recommendation_latitude, plan.latitude, abs_tol=LOCATION_MATCH_TOLERANCE)
        and math.isclose(recommendation_longitude, plan.longitude, abs_tol=LOCATION_MATCH_TOLERANCE)
    )
    if not same_location:
        return JsonResponse({
            "error": f"Lokasi rekomendasi tidak sama dengan lokasi plan ({plan.location_name or 'lokasi plan'}). Tanaman tidak dapat ditambahkan."
        }, status=409)

    plant = get_object_or_404(Plant, pk=body.get("plant_id"))
    pot   = None
    if body.get("pot_id"):
        pot = get_object_or_404(Pot, pk=body["pot_id"])
        if pot.owner_id not in (None, request.user.pk):
            return JsonResponse({"error": "Pot tidak dapat digunakan."}, status=403)

    item = PlanPlant.objects.create(
        plan     = plan,
        plant    = plant,
        pot      = pot,
        quantity = body.get("quantity", 1),
        note     = body.get("note", ""),
    )
    return JsonResponse({"id": item.pk}, status=201)


@login_required
@require_http_methods(["PUT", "DELETE"])
def planplant_detail(request, plan_pk, pk):
    plan = get_object_or_404(Plan, pk=plan_pk, owner=request.user)
    item = get_object_or_404(PlanPlant, pk=pk, plan=plan)

    if request.method == "PUT":
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "JSON tidak valid."}, status=400)

        if "quantity" in body:
            item.quantity = body["quantity"]
        if "note" in body:
            item.note = body["note"]
        if "pot_id" in body:
            item.pot = get_object_or_404(Pot, pk=body["pot_id"]) if body["pot_id"] else None
            if item.pot and item.pot.owner_id not in (None, request.user.pk):
                return JsonResponse({"error": "Pot tidak dapat digunakan."}, status=403)
        item.save()
        return JsonResponse({"ok": True})

    # DELETE
    item.delete()
    return JsonResponse({"ok": True})
