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
import calendar
from datetime import date


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
def garden_journal_evaluation(request):
    today = timezone.localdate()
    current_month = today.replace(day=1)

    # Prepare the current month and previous 11 months.
    month_options = []
    cursor = current_month

    for _ in range(12):
        month_options.append({
            "value": cursor.strftime("%Y-%m"),
            "label": cursor.strftime("%B %Y"),
        })
        cursor = (cursor - timedelta(days=1)).replace(day=1)

    valid_months = {
        option["value"] for option in month_options
    }

    selected_month = request.GET.get(
        "month",
        current_month.strftime("%Y-%m"),
    )

    # Ignore unsupported or invalid month values.
    if selected_month not in valid_months:
        selected_month = current_month.strftime("%Y-%m")

    month_start = date.fromisoformat(
        f"{selected_month}-01"
    )

    next_month_start = (
        month_start.replace(day=28) + timedelta(days=4)
    ).replace(day=1)

    # Restrict every query to the authenticated user.
    month_entries = GardenJournalEntry.objects.filter(
        user=request.user,
        entry_date__gte=month_start,
        entry_date__lt=next_month_start,
    ).order_by("-entry_date", "-created_at")

    total_entries = month_entries.count()

    harvest_count = month_entries.filter(
        entry_type="harvest"
    ).count()

    problem_count = month_entries.filter(
        entry_type="issue"
    ).count()

    plant_count = (
        month_entries.order_by()
        .values("plant_name")
        .distinct()
        .count()
    )

    growth_count = month_entries.filter(
        entry_type="growth"
    ).count()

    flowering_count = month_entries.filter(
        entry_type="flowering"
    ).count()

    # Group entries by plant name for the monthly table.
    plant_summary = (
        month_entries.order_by()
        .values("plant_name")
        .annotate(
            entry_count=Count("pk"),
            harvest_count=Count(
                "pk",
                filter=Q(entry_type="harvest"),
            ),
            issue_count=Count(
                "pk",
                filter=Q(entry_type="issue"),
            ),
        )
        .order_by("plant_name")
    )

    # List distinct weather notes actually recorded this month.
    weather_notes = (
        month_entries.exclude(weather_summary="")
        .order_by()
        .values("weather_summary")
        .annotate(entry_count=Count("pk"))
        .order_by("-entry_count", "weather_summary")
    )

    # Build weekly entry counts using calendar weeks.
    first_weekday, days_in_month = calendar.monthrange(
        month_start.year,
        month_start.month,
    )

    week_count = (
        first_weekday + days_in_month + 6
    ) // 7

    weekly_activity = [
        {
            "label": f"Week {index + 1}",
            "count": 0,
            "bar_height": 0,
        }
        for index in range(week_count)
    ]

    for entry in month_entries:
        week_index = (
            entry.entry_date.day - 1 + first_weekday
        ) // 7

        weekly_activity[week_index]["count"] += 1

    max_week_count = max(
        (week["count"] for week in weekly_activity),
        default=0,
    )

    for week in weekly_activity:
        if max_week_count:
            week["bar_height"] = round(
                week["count"] / max_week_count * 100
            )

    # Generate summaries from actual recorded activity.
    what_went_well = []

    if total_entries:
        what_went_well.append(
            f"You recorded {total_entries} journal entries this month."
        )

    if growth_count or flowering_count:
        what_went_well.append(
            f"You recorded {growth_count} growth and "
            f"{flowering_count} flowering entries."
        )

    if harvest_count:
        what_went_well.append(
            f"You recorded {harvest_count} harvest entries."
        )

    if not what_went_well:
        what_went_well.append(
            "No journal activity has been recorded for this month yet."
        )

    next_month_suggestions = []

    if problem_count:
        next_month_suggestions.append(
            f"Review the {problem_count} problem entries and "
            "record any changes in plant condition."
        )

    if harvest_count:
        next_month_suggestions.append(
            "Continue recording harvest quantities and units "
            "to compare future harvests."
        )

    if not next_month_suggestions:
        next_month_suggestions.append(
            "Record growth, flowering, harvests, or problems "
            "you observe during the next month."
        )

    context = {
        "selected_month": selected_month,
        "selected_month_label": month_start.strftime("%B %Y"),
        "month_options": month_options,
        "total_entries": total_entries,
        "harvest_count": harvest_count,
        "problem_count": problem_count,
        "plant_count": plant_count,
        "plant_summary": plant_summary,
        "weather_notes": weather_notes,
        "weekly_activity": weekly_activity,
        "what_went_well": what_went_well,
        "next_month_suggestions": next_month_suggestions,
    }

    return render(
        request,
        "garden_journal_evaluation.html",
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
            "page_title": "New journal entry",
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
            "page_title": "Edit journal entry",
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


