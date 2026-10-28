from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from .models import GrowingSpace

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET

from .forms import GrowingSpaceForm
from .geocoding import (
    GeocodingServiceError,
    get_location_by_id,
    search_locations,
)

@login_required(login_url="login")
def space_list(request):
    owned_spaces = GrowingSpace.objects.filter(
        user=request.user
    )

    total_count = owned_spaces.count()
    indoor_count = owned_spaces.filter(
        environment=GrowingSpace.Environment.INDOOR
    ).count()
    outdoor_count = owned_spaces.filter(
        environment=GrowingSpace.Environment.OUTDOOR
    ).count()
    search_query = request.GET.get(
        "q", ""
    ).strip()[:100]
    selected_environment = request.GET.get(
        "environment", ""
    )

    if selected_environment not in ("indoor", "outdoor"):
        selected_environment = ""

    spaces = owned_spaces

    if search_query:
        spaces = spaces.filter(
            Q(name__icontains=search_query) |
            Q(city__icontains=search_query)
        )

    if selected_environment:
        spaces = spaces.filter(
            environment=selected_environment
        )

    return render(
        request,
        "garden_setup/space_list.html",
        {
            "spaces": spaces,
            "search_query": search_query,
            "selected_environment": selected_environment,
            "total_count": total_count,
            "indoor_count": indoor_count,
            "outdoor_count": outdoor_count,
            "has_filters": bool(
                search_query or selected_environment
            ),
        },
    )

@login_required(login_url="login")
@require_GET
def location_search(request):
    """Mengirim hasil autocomplete lokasi sebagai JSON."""

    query = request.GET.get("q", "").strip()[:80]

    if len(query) < 2:
        return JsonResponse({"results": []})

    try:
        results = search_locations(query)
    except GeocodingServiceError:
        return JsonResponse(
            {
                "results": [],
                "error": "Location service is unavailable. Please try again.",
            },
            status=503,
        )

    return JsonResponse({"results": results})

def _prepare_location_data(post_data, instance=None):
    """Verifikasi lokasi dan gunakan metadata resmi dari server."""

    data = post_data.copy()
    raw_id = str(data.get("geocoding_id", "")).strip()

    if not raw_id.isdigit():
        return data, "Please select a city from the suggestions."

    location_id = int(raw_id)

    if not (0 < location_id <= 9223372036854775807):
        return data, "Invalid location. Please select a city again."

    # Pada edit, lokasi lama dipertahankan
    if instance is not None and location_id == instance.geocoding_id:
        if data.get("city", "").strip() != instance.city:
            return (
                data,
                "Please select the new city from the suggestions.",
            )
        location = {
            "id": instance.geocoding_id,
            "name": instance.city,
            "region": instance.region,
            "country": instance.country,
            "latitude": instance.latitude,
            "longitude": instance.longitude,
            "timezone": instance.timezone,
        }

    else:
        try:
            location = get_location_by_id(location_id)
        except GeocodingServiceError:
            return (
                data,
                "Location service is unavailable. Please try again.",
            )

        if location is None:
            return (
                data,
                "Location could not be verified. Please select another city.",
            )

    data["geocoding_id"] = str(location["id"])
    data["city"] = str(location["name"])
    data["region"] = str(location["region"])
    data["country"] = str(location["country"])
    data["latitude"] = str(location["latitude"])
    data["longitude"] = str(location["longitude"])
    data["timezone"] = str(location["timezone"])

    return data, None

def _space_form(request, instance=None):
    """Logika bersama untuk halaman Create dan Edit."""

    is_edit = instance is not None

    if request.method == "POST":
        data, location_error = _prepare_location_data(
            request.POST,
            instance=instance,
        )

        form = GrowingSpaceForm(
            data=data,
            instance=instance,
        )

        form_is_valid = form.is_valid()

        if location_error:
            form.add_error("city", location_error)

        if form_is_valid and not location_error:
            space = form.save(commit=False)
            space.user = request.user
            space.save()

            if is_edit:
                messages.success(
                    request,
                    "Growing space updated successfully.",
                )
            else:
                messages.success(
                    request,
                    "Growing space created successfully.",
                )

            return redirect("garden_setup:space_list")

    else:
        form = GrowingSpaceForm(instance=instance)

    return render(
        request,
        "garden_setup/space_form.html",
        {
            "form": form,
            "space": instance,
            "is_edit": is_edit,
        },
    )

@login_required(login_url="login")
def space_create(request):
    """Membuat Growing Space baru."""
    return _space_form(request)

@login_required(login_url="login")
def space_edit(request, pk):
    """Mengedit Growing Space milik pengguna login."""

    space = get_object_or_404(
        GrowingSpace,
        pk=pk,
        user=request.user,
    )

    return _space_form(request, instance=space)
