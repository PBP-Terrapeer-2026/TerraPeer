from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import redirect, render
import datetime
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import GardenJournalEntry
from .forms import GardenJournalEntryForm
from datetime import timedelta
from django.db.models import Count, Q
from django.utils import timezone


def show_main(request):
    return render(request, "index.html")

def register(request):
    form = UserCreationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Akun berhasil dibuat. Silakan login.")
        return redirect("login")

    context = {
        "name": "Burhan",
        "form": form,
    }
    return render(request, "register.html", context)

def login_user(request):
    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        response = redirect("show_main")
        response.set_cookie('last_login', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return response

    context = {
        "name": "Burhan",
        "form": form,
    }
    return render(request, "login.html", context)

def logout_user(request):
    logout(request)
    response = redirect("show_main")
    response.delete_cookie('last_login')
    return response

# Garden Journal


@login_required
def garden_journal(request):
    # mengambil hanya jurnal milik pengguna yang sedang login
    all_entries = GardenJournalEntry.objects.filter(
        user=request.user
    ).order_by("-entry_date", "-created_at")

    entries = all_entries

    #mengambil parameter pencarian dan filter dari URL
    search_query = request.GET.get("q", "").strip()
    selected_plant = request.GET.get("plant", "").strip()
    selected_event = request.GET.get("event", "").strip()
    selected_period = request.GET.get("period", "3m")

    #makesure jenis event dan periode valid
    valid_event_types = {
        value for value, label in GardenJournalEntry.ENTRY_TYPE_CHOICES
    }

    if selected_event not in valid_event_types:
        selected_event = ""

    period_days = {
        "1m": 30,
        "3m": 90,
        "6m": 180,
    }

    if selected_period not in {"1m", "3m", "6m", "all"}:
        selected_period = "3m"

    #cari pada nama tanaman, judul, catatan, dan cuaca
    if search_query:
        entries = entries.filter(
            Q(plant_name__icontains=search_query)
            | Q(title__icontains=search_query)
            | Q(notes__icontains=search_query)
            | Q(weather_summary__icontains=search_query)
        )

    # Filter berdasarkan nama tanaman.
    if selected_plant:
        entries = entries.filter(plant_name=selected_plant)

    # Filter berdasarkan jenis peristiwa.
    if selected_event:
        entries = entries.filter(entry_type=selected_event)

    # Filter periode tanggal.
    if selected_period != "all":
        today = timezone.localdate()
        start_date = today - timedelta(
            days=period_days[selected_period]
        )
        entries = entries.filter(entry_date__gte=start_date)

    #daftar tanaman yang pernah dicatat oleh pengguna
    plant_options = (
        all_entries.order_by()
        .values_list("plant_name", flat=True)
        .distinct()
        .order_by("plant_name")
    )

    #jumlah catatan per tanaman di panel "By plant".
    plant_summary = (
        all_entries.order_by()
        .values("plant_name")
        .annotate(entry_count=Count("pk"))
        .order_by("-entry_count", "plant_name")
    )

    #ringkasan = dihitung dari seluruh jurnal milik pengguna,
    
    total_entries = all_entries.count()

    harvest_count = all_entries.filter(
        entry_type="harvest"
    ).count()

    problem_count = all_entries.filter(
        entry_type="issue"
    ).count()

    #ambil catatan cuaca terbaru yang benar-benar tersimpan
    latest_weather_entry = (
        all_entries.exclude(weather_summary="")
        .first()
    )

    context = {
        "entries": entries,
        "total_entries": total_entries,
        "harvest_count": harvest_count,
        "problem_count": problem_count,
        "search_query": search_query,
        "selected_plant": selected_plant,
        "selected_event": selected_event,
        "selected_period": selected_period,
        "plant_options": plant_options,
        "entry_type_choices": GardenJournalEntry.ENTRY_TYPE_CHOICES,
        "plant_summary": plant_summary,
        "latest_weather_entry": latest_weather_entry,
    }

    return render(
        request,
        "garden_journal.html",
        context,
    )



@login_required
def garden_journal_create(request):
    if request.method == "POST":
        form = GardenJournalEntryForm(request.POST)

        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()

            messages.success(
                request,
                "Journal entry successfully created.",
            )
            return redirect("garden_journal")
    else:
        form = GardenJournalEntryForm()

    return render(
        request,
        "garden_journal_form.html",
        {
            "form": form,
            "page_title": "Add Journal Entry",
        },
    )


@login_required
def garden_journal_edit(request, entry_id):
    entry = get_object_or_404(
        GardenJournalEntry,
        pk=entry_id,
        user=request.user,
    )

    if request.method == "POST":
        form = GardenJournalEntryForm(
            request.POST,
            instance=entry,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Journal entry successfully updated.",
            )
            return redirect("garden_journal")
    else:
        form = GardenJournalEntryForm(instance=entry)

    return render(
        request,
        "garden_journal_form.html",
        {
            "form": form,
            "page_title": "Edit Catatan Jurnal",
        },
    )


@login_required
def garden_journal_delete(request, entry_id):
    entry = get_object_or_404(
        GardenJournalEntry,
        pk=entry_id,
        user=request.user,
    )

    if request.method == "POST":
        entry.delete()
        messages.success(
            request,
            "Journal entry successfully deleted.",
        )
        return redirect("garden_journal")

    return render(
        request,
        "garden_journal_confirm_delete.html",
        {"entry": entry},
    )


