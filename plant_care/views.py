from functools import wraps
from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Case, When, Value, IntegerField, Count, Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .models import CareTask, PlantCareSpace, LegacyPlant
from .integration import plants_for, plant_space, plant_today, plant_timezone
from .forms import CareTaskForm, PlantCareSpaceForm, LegacyPlantLinkForm
from .services import complete_task, undo_completion, UndoCompletionConflict
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
    return get_object_or_404(plants_for(request.user), pk=pk)


def owned_task(request, pk, lock=False):
    query = CareTask.objects.select_related("plant__care_location__growing_space")
    if lock:
        query = query.select_for_update(of=("self",))
    return get_object_or_404(query, pk=pk, plant__owner=request.user)


def fragment(request, name, context, status=200):
    return JsonResponse(
        {"html": render_to_string("care/" + name + ".html", context, request=request)},
        status=status,
    )


def list_context(request, plant):
    """Build one consistent snapshot for the initial page and AJAX refreshes."""
    today = plant_today(plant)
    time_filter = request.GET.get("time", "all")
    status_filter = request.GET.get("status", "all")
    action_filter = request.GET.get("action", "")
    overdue_filter = request.GET.get("overdue") == "1"
    if time_filter not in {"all", "today", "upcoming"}:
        time_filter = "all"
    if status_filter not in {"all", "Pending", "Completed"}:
        status_filter = "all"
    if action_filter not in dict(CareTask.ACTIONS):
        action_filter = ""
    selected_date = None
    try:
        selected_date = date.fromisoformat(request.GET.get("date", ""))
        # Leave room for previous/next-week links near Python's date limits.
        if not date(2, 1, 1) <= selected_date <= date(9998, 12, 20):
            selected_date = None
    except ValueError:
        pass

    all_tasks = CareTask.objects.filter(plant=plant)
    totals = all_tasks.aggregate(
        total=Count("pk"), pending=Count("pk", filter=Q(status="Pending"))
    )
    anchor = selected_date or today
    start = anchor - timedelta(days=anchor.weekday())
    # One grouped query replaces a count query for every day in the week.
    week_rows = list(
        all_tasks.filter(due_date__gte=start, due_date__lt=start + timedelta(days=7))
        .order_by()
        .values("due_date")
        .annotate(total=Count("pk"), done=Count("pk", filter=Q(status="Completed")))
    )
    counts = {row["due_date"]: row["total"] for row in week_rows}
    week_total = sum(row["total"] for row in week_rows)
    week_done = sum(row["done"] for row in week_rows)
    calendar = [
        {
            "date": start + timedelta(days=i),
            "count": counts.get(start + timedelta(days=i), 0),
            "selected": start + timedelta(days=i) == selected_date,
        }
        for i in range(7)
    ]

    tasks = all_tasks.select_related("plant__care_location__growing_space")
    if time_filter == "today":
        tasks = tasks.filter(due_date=today)
    elif time_filter == "upcoming":
        tasks = tasks.filter(due_date__gt=today)
    if status_filter != "all":
        tasks = tasks.filter(status=status_filter)
    if selected_date:
        tasks = tasks.filter(due_date=selected_date)
    if action_filter:
        tasks = tasks.filter(action_type=action_filter)
    if overdue_filter:
        tasks = tasks.filter(status="Pending", due_date__lt=today)
    tasks = tasks.annotate(
        order=Case(
            When(status="Pending", then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    ).order_by("order", "due_date", "pk")
    return {
        "plant": plant,
        "calendar": calendar,
        "week_start": start,
        "week_end": start + timedelta(days=6),
        "previous_week": start - timedelta(days=7),
        "next_week": start + timedelta(days=7),
        "selected_date": selected_date,
        "week_total": week_total,
        "week_done": week_done,
        "tasks": tasks,
        "has_tasks": totals["total"] > 0,
        "pending_count": totals["pending"],
        "time_filter": time_filter,
        "status_filter": status_filter,
        "action_filter": action_filter,
        "overdue_filter": overdue_filter,
        "actions": CareTask.ACTIONS,
    }


@login_required(login_url="login")
@require_GET
def choose(request):
    plants = plants_for(request.user)
    first = plants.active().first() or plants.first()
    if first:
        return redirect("care:page", pk=first.pk)
    return render(request, "care/no_plants.html")


@login_required(login_url="login")
@require_GET
def page(request, pk):
    plant = owned_plant(request, pk)
    context = list_context(request, plant)
    context["plants"] = plants_for(request.user)
    context["space_form"] = PlantCareSpaceForm(
        user=request.user,
        instance=PlantCareSpace.objects.filter(plant=plant).first(),
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
    return JsonResponse(
        {
            "html": html,
            "pending_count": context["pending_count"],
            "calendar_html": render_to_string(
                "care/calendar.html", context, request=request
            ),
            "summary_html": render_to_string(
                "care/summary.html", context, request=request
            ),
        }
    )


@api_auth
@require_GET
def detail(request, pk):
    task = owned_task(request, pk)
    next_date = None
    if (
        task.repeat_every
        and (task.plant.status == "active")
        and task.status == "Pending"
    ):
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
            "plant_timezone": str(plant_timezone(task.plant)),
            "completed_local": (
                task.completed_at.astimezone(plant_timezone(task.plant))
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
    if plant.status != "active":
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
    elif changed and task.repeat_every and not (task.plant.status == "active"):
        message += " No next reminder: the plant is not active."
    return JsonResponse(
        {
            "message": message,
            "next_id": following.pk if following else None,
            "undo_url": reverse("care:undo", args=[task.pk]),
        }
    )


@api_auth
@require_POST
def undo(request, pk):
    task = owned_task(request, pk)
    try:
        task, changed = undo_completion(task.pk, request.user)
    except CareTask.DoesNotExist:
        return JsonResponse({"message": "Task no longer exists."}, status=404)
    except (UndoCompletionConflict, OverflowError) as exc:
        message = (
            str(exc)
            if isinstance(exc, UndoCompletionConflict)
            else "Cannot undo: the reminder dates are inconsistent."
        )
        return JsonResponse({"message": message}, status=409)
    return JsonResponse(
        {
            "message": (
                "Completion undone. Task is back in To do."
                if changed
                else "This task is already in To do."
            )
        }
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
        garden = plant_space(plant)
        data = forecast(garden)
        try:
            index = max(0, min(int(request.GET.get("day", "0")), len(data["days"]) - 1))
        except ValueError:
            index = 0
        data["selected"] = index
        data["day"] = data["days"][index] if data["days"] else None
        return fragment(
            request, "weather", {"plant": plant, "garden": garden, "forecast": data}
        )
    except ForecastUnavailable:
        return fragment(
            request,
            "weather",
            {
                "plant": plant,
                "garden": plant_space(plant),
                "forecast": {"state": "error"},
            },
            status=503,
        )


@api_auth
@require_POST
def set_space(request, pk):
    plant = owned_plant(request, pk)
    instance = PlantCareSpace.objects.filter(plant=plant).first()
    if instance is None:
        instance = PlantCareSpace(plant=plant)
    form = PlantCareSpaceForm(request.POST, user=request.user, instance=instance)
    if not form.is_valid():
        return JsonResponse(
            {"message": "Choose one of your growing spaces.", "errors": form.errors},
            status=422,
        )
    PlantCareSpace.objects.update_or_create(
        plant=plant,
        defaults={"growing_space": form.cleaned_data["growing_space"]},
    )
    return JsonResponse(
        {"message": "Care location saved. Forecast and calendar updated."}
    )


@login_required(login_url="login")
@require_http_methods(["GET", "POST"])
@transaction.atomic
def link_legacy(request):
    """The owner maps old tasks explicitly; names and IDs are never guessed."""
    form = LegacyPlantLinkForm(
        request.POST if request.method == "POST" else None,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        old = get_object_or_404(
            LegacyPlant.objects.select_for_update(),
            pk=form.cleaned_data["legacy_plant"].pk,
            garden__owner=request.user,
        )
        plant = form.cleaned_data["plant"]
        CareTask.objects.filter(legacy_plant=old, plant__isnull=True).update(
            plant=plant
        )
        return redirect("care:page", pk=plant.pk)
    return render(request, "care/link_legacy.html", {"form": form})
