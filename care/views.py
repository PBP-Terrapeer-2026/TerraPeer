from functools import wraps
from datetime import timedelta
from zoneinfo import ZoneInfo
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Case, When, Value, IntegerField
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .models import Plant, CareTask
from .forms import CareTaskForm
from .services import complete_task
from .weather import forecast, ForecastUnavailable


def api_auth(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {
                    "message": "Your session expired. Sign in again.",
                    "login_url": reverse("login"),
                },
                status=401,
            )
        return view(request, *args, **kwargs)

    return wrapped


def owned_plant(request, pk):
    return get_object_or_404(
        Plant.objects.select_related("garden"), pk=pk, garden__owner=request.user
    )


def owned_task(request, pk, lock=False):
    query = CareTask.objects.select_related("plant__garden")
    if lock:
        query = query.select_for_update()
    return get_object_or_404(query, pk=pk, plant__garden__owner=request.user)


def fragment(request, name, context, status=200):
    return JsonResponse(
        {"html": render_to_string("care/" + name + ".html", context, request=request)},
        status=status,
    )


def list_context(request, plant):
    time = request.GET.get("time", "all")
    status = request.GET.get("status", "all")
    if time not in ["all", "today", "upcoming"]:
        time = "all"
    if status not in ["all", "Pending", "Completed"]:
        status = "all"
    all_tasks = CareTask.objects.filter(plant=plant).select_related("plant__garden")
    tasks = all_tasks
    if time == "today":
        tasks = tasks.filter(due_date=plant.today)
    if time == "upcoming":
        tasks = tasks.filter(due_date__gt=plant.today)
    if status != "all":
        tasks = tasks.filter(status=status)
    tasks = tasks.annotate(
        order=Case(
            When(status="Pending", then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    ).order_by("order", "due_date", "pk")
    return {
        "plant": plant,
        "tasks": tasks,
        "has_tasks": all_tasks.exists(),
        "pending_count": all_tasks.filter(status="Pending").count(),
        "time_filter": time,
        "status_filter": status,
    }


@require_GET
def landing(request):
    plants = (
        Plant.objects.filter(garden__owner=request.user)
        if request.user.is_authenticated
        else Plant.objects.none()
    )
    first = plants.filter(status="Active").first() or plants.first()
    plant_urls = {}
    for p in plants.order_by("pk"):
        plant_urls.setdefault(p.image, reverse("care:page", args=[p.pk]))
    config = {
        "careUrl": (
            reverse("care:page", args=[first.pk]) if first else reverse("care:choose")
        ),
        "plantUrls": plant_urls,
        "initialView": "home" if request.user.is_authenticated else "public",
    }
    return render(request, "care/landing.html", {"landing_config": config})


@login_required
@require_GET
def choose(request):
    plants = Plant.objects.filter(garden__owner=request.user).select_related("garden")
    first = plants.filter(status="Active").first() or plants.first()
    if first:
        return redirect("care:page", pk=first.pk)
    return render(request, "care/no_plants.html")


@login_required
@require_GET
def page(request, pk):
    plant = owned_plant(request, pk)
    context = list_context(request, plant)
    context["plants"] = Plant.objects.filter(garden__owner=request.user).select_related(
        "garden"
    )
    context["title"] = "Plant Care · " + plant.name
    return render(request, "care/page.html", context)


@api_auth
@require_GET
def task_list(request, pk):
    context = list_context(request, owned_plant(request, pk))
    html = render_to_string("care/task_list.html", context, request=request)
    if request.headers.get("HX-Request") == "true":
        return HttpResponse(html)
    return JsonResponse({"html": html, "pending_count": context["pending_count"]})


@api_auth
@require_GET
def detail(request, pk):
    task = owned_task(request, pk)
    next_date = None
    if task.repeat_every and task.plant.active and task.status == "Pending":
        try:
            next_date = task.due_date + timedelta(days=task.repeat_every)
        except OverflowError:
            pass
    return fragment(
        request,
        "task_detail",
        {
            "task": task,
            "next_date": next_date,
            "completed_local": (
                task.completed_at.astimezone(ZoneInfo(task.plant.garden.timezone_name))
                if task.completed_at
                else None
            ),
        },
    )


def form_response(request, form, plant, task=None, code=200):
    for name in form.errors:
        if name in form.fields:
            form.fields[name].widget.attrs["aria-invalid"] = "true"
    return fragment(
        request, "task_form", {"form": form, "plant": plant, "task": task}, status=code
    )


@api_auth
@require_http_methods(["GET", "POST"])
def add(request, pk):
    plant = owned_plant(request, pk)
    if not plant.active:
        return JsonResponse(
            {"message": "New tasks require an active plant."}, status=409
        )
    form = CareTaskForm(request.POST if request.method == "POST" else None)
    if request.method == "GET":
        return form_response(request, form, plant)
    if not form.is_valid():
        return form_response(request, form, plant, code=422)
    task = form.save(commit=False)
    task.plant = plant
    task.save()
    return JsonResponse(
        {
            "message": "Care task added. The list keeps your current filters.",
            "id": task.pk,
        },
        status=201,
    )


@api_auth
@require_http_methods(["GET", "POST"])
@transaction.atomic
def edit(request, pk):
    task = owned_task(request, pk, lock=True)
    if task.status != "Pending":
        return JsonResponse(
            {"message": "Completed tasks cannot be edited."}, status=409
        )
    form = CareTaskForm(
        request.POST if request.method == "POST" else None, instance=task
    )
    if request.method == "GET":
        return form_response(request, form, task.plant, task)
    if not form.is_valid():
        return form_response(request, form, task.plant, task, 422)
    form.save()
    return JsonResponse(
        {"message": "Changes saved. This task stays linked to the same plant."}
    )


@api_auth
@require_POST
def complete(request, pk):
    task = owned_task(request, pk)
    try:
        task, following, changed = complete_task(task.pk, request.user)
    except CareTask.DoesNotExist:
        return JsonResponse({"message": "Task no longer exists."}, status=404)
    except OverflowError:
        return JsonResponse(
            {
                "message": "The next date is outside the supported range. Edit the interval first."
            },
            status=409,
        )
    message = "Task completed." if changed else "This task was already completed."
    if following:
        message += f" Next reminder: {following.due_date:%d %b %Y}."
    elif changed and task.repeat_every and not task.plant.active:
        message += " No next reminder: the plant is not active."
    return JsonResponse(
        {"message": message, "next_id": following.pk if following else None}
    )


@api_auth
@require_http_methods(["GET", "POST"])
@transaction.atomic
def delete(request, pk):
    task = owned_task(request, pk, lock=True)
    if request.method == "GET":
        return fragment(request, "task_delete", {"task": task})
    repeated = task.status == "Pending" and task.repeat_every
    task.delete()  # No scheduler exists: a next task only arises from completion.
    return JsonResponse(
        {
            "message": (
                "Task deleted. Repetition stopped; completed history kept."
                if repeated
                else "Task deleted."
            )
        }
    )


@api_auth
@require_GET
def weather_view(request, pk):
    plant = owned_plant(request, pk)
    try:
        data = forecast(plant.garden)
        try:
            index = max(0, min(int(request.GET.get("day", "0")), len(data["days"]) - 1))
        except ValueError:
            index = 0
        data["selected"] = index
        data["day"] = data["days"][index] if data["days"] else None
        return fragment(request, "weather", {"plant": plant, "forecast": data})
    except ForecastUnavailable:
        return fragment(
            request,
            "weather",
            {"plant": plant, "forecast": {"state": "error"}},
            status=503,
        )
