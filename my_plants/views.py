from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, OuterRef, Q, Subquery
from django.db.models.deletion import ProtectedError, RestrictedError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import CheckInForm, PhotoForm, PlantFilterForm, PlantForm, StageForm
from .models import Plant, PlantCheckIn, PlantPhoto
from .services import CatalogUnavailable, search_species

PAGE_SIZE = 12


def _wants_json(request):
    return 'application/json' in request.headers.get('Accept', '')


def _owned_plant(request, pk):
    """Every private view goes through here, so a plant ID from another account is a 404."""
    return get_object_or_404(Plant.objects.for_user(request.user), pk=pk)


def _latest_photo_id():
    return Subquery(PlantPhoto.objects.filter(plant=OuterRef('pk')).order_by('-created_at', '-pk').values('pk')[:1])


def _cover_url(plant):
    cover_id = getattr(plant, 'cover_id', None)
    if cover_id is None and not hasattr(plant, 'cover_id'):
        cover_id = plant.photos.order_by('-created_at', '-pk').values_list('pk', flat=True).first()
    return PlantPhoto(pk=cover_id, plant=plant).get_absolute_url() if cover_id else ''


def _serialize(plant):
    return {
        'id': plant.pk, 'name': plant.name, 'species_name': plant.species_name,
        'planted_on': plant.planted_on.isoformat(), 'days_growing': plant.days_growing,
        'growth_stage': plant.growth_stage, 'growth_stage_label': plant.get_growth_stage_display(),
        'status': plant.status, 'notes': plant.notes, 'perenual_species_id': plant.perenual_species_id,
        'cover_photo_url': _cover_url(plant), 'url': plant.get_absolute_url(),
    }


def _serialize_photo(photo):
    return {
        'id': photo.pk, 'url': photo.get_absolute_url(), 'stage': photo.stage,
        'stage_label': photo.get_stage_display(), 'kind': photo.kind, 'caption': photo.caption,
        'day': photo.day_number, 'width': photo.width, 'height': photo.height,
        'created_at': photo.created_at.isoformat(),
    }


def _save_photo(plant, form, kind):
    if not form.processed_photo:
        return None
    data, width, height = form.processed_photo
    return PlantPhoto.objects.create(
        plant=plant, image=data, width=width, height=height, stage=plant.growth_stage, kind=kind,
        caption=form.cleaned_data.get('caption', '') or '',
    )


def _stage_steps(plant):
    """Ordered stages for the stepper; earlier stages count as done (stages may be skipped)."""
    stages = list(Plant.Stage)
    current = stages.index(Plant.Stage(plant.growth_stage))
    return [
        {'value': stage.value, 'label': stage.label,
         'state': 'done' if i < current or plant.growth_stage == Plant.Stage.FINISHED else 'current' if i == current else 'todo'}
        for i, stage in enumerate(stages)
    ]


def _stats(owned):
    return owned.aggregate(
        total=Count('pk'),
        active=Count('pk', filter=~Q(growth_stage=Plant.Stage.FINISHED)),
        growing=Count('pk', filter=Q(growth_stage=Plant.Stage.GROWING)),
        blooming=Count('pk', filter=Q(growth_stage__in=[Plant.Stage.FLOWERING, Plant.Stage.FRUITING])),
        harvesting=Count('pk', filter=Q(growth_stage=Plant.Stage.HARVESTING)),
        finished=Count('pk', filter=Q(growth_stage=Plant.Stage.FINISHED)),
    )


def _list_context(request):
    owned = Plant.objects.for_user(request.user)
    form = PlantFilterForm(request.GET)
    plants = owned.annotate(cover_id=_latest_photo_id())
    if form.is_valid():
        values = form.cleaned_data
        if values['q']:
            plants = plants.filter(Q(name__icontains=values['q']) | Q(species_name__icontains=values['q']))
        if values['stage']:
            plants = plants.filter(growth_stage=values['stage'])
        if values['status'] == 'active':
            plants = plants.active()
        elif values['status'] == 'finished':
            plants = plants.filter(growth_stage=Plant.Stage.FINISHED)
        plants = plants.order_by(*PlantFilterForm.ORDERING[values['sort'] or 'newest'])
    else:
        plants = plants.none()
    page = Paginator(plants, PAGE_SIZE).get_page(request.GET.get('page'))
    query = request.GET.copy()
    query.pop('page', None)
    return {
        'filter_form': form, 'page_obj': page, 'querystring': query.urlencode(),
        'is_filtered': any(request.GET.get(key) for key in ('q', 'stage', 'status')),
        'stats': _stats(owned),
    }


@login_required
@require_GET
def plant_list(request):
    return render(request, 'my_plants/list.html', _list_context(request))


@login_required
@require_GET
def plant_fragment(request):
    """HTML fragment for the AJAX filter; same filters and pagination as the list."""
    return render(request, 'my_plants/_results.html', _list_context(request))


def _detail_context(plant, stage_form=None, check_in_form=None, photo_form=None):
    photos = list(plant.photos.without_image())
    for photo in photos:
        photo.plant = plant
    return {
        'plant': plant, 'stage_form': stage_form or StageForm(instance=plant), 'stage_steps': _stage_steps(plant),
        'check_in_form': check_in_form or CheckInForm(), 'check_ins': plant.check_ins.all()[:8],
        'check_in_count': plant.check_ins.count(),
        'photos': photos, 'cover': photos[-1] if photos else None, 'photo_form': photo_form or PhotoForm(),
    }


def _serialize_check_in(check_in):
    return {
        'id': check_in.pk, 'plant': check_in.plant_id, 'condition': check_in.condition,
        'condition_label': check_in.get_condition_display(), 'note': check_in.note,
        'needs_attention': check_in.needs_attention, 'created_at': check_in.created_at.isoformat(),
    }


@login_required
@require_GET
def plant_detail(request, pk):
    return render(request, 'my_plants/detail.html', _detail_context(_owned_plant(request, pk)))


@login_required
@require_http_methods(['GET', 'POST'])
def plant_create(request):
    form = PlantForm(request.POST, request.FILES) if request.method == 'POST' else PlantForm(
        initial={'species_name': request.GET.get('species', '')[:160]})
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            plant = form.save(commit=False)
            plant.owner = request.user
            plant.save()
            _save_photo(plant, form, PlantPhoto.Kind.START)
        if _wants_json(request):
            return JsonResponse({'plant': _serialize(plant)}, status=201)
        messages.success(request, f'{plant.name} has been added to My Plants.')
        return redirect(plant)
    if request.method == 'POST' and _wants_json(request):
        return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
    return render(request, 'my_plants/form.html', {'form': form, 'is_edit': False},
                  status=400 if request.method == 'POST' else 200)


@login_required
@require_http_methods(['GET', 'POST'])
def plant_edit(request, pk):
    plant = _owned_plant(request, pk)
    form = PlantForm(request.POST, request.FILES, instance=plant) if request.method == 'POST' else PlantForm(instance=plant)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            plant = form.save()
            _save_photo(plant, form, PlantPhoto.Kind.PROGRESS)
        if _wants_json(request):
            return JsonResponse({'plant': _serialize(plant)})
        messages.success(request, 'Plant details updated.')
        return redirect(plant)
    if request.method == 'POST' and _wants_json(request):
        return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
    return render(request, 'my_plants/form.html', {'form': form, 'plant': plant, 'is_edit': True},
                  status=400 if request.method == 'POST' else 200)


@login_required
@require_POST
def plant_stage(request, pk):
    plant = _owned_plant(request, pk)
    form = StageForm(request.POST, request.FILES, instance=plant)
    if not form.is_valid():
        if _wants_json(request):
            return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
        plant.refresh_from_db()
        return render(request, 'my_plants/detail.html', _detail_context(plant, stage_form=form), status=400)
    changed = form.stage_changed
    with transaction.atomic():
        plant = form.save()
        photo = _save_photo(plant, form, PlantPhoto.Kind.STAGE if changed else PlantPhoto.Kind.PROGRESS)
    if _wants_json(request):
        payload = {'plant': _serialize(plant), 'steps': _stage_steps(plant), 'photo': None, 'photo_html': ''}
        if photo:
            payload['photo'] = _serialize_photo(photo)
            payload['photo_html'] = render_to_string('my_plants/_photo_tile.html', {'photo': photo, 'plant': plant}, request=request)
        if plant.growth_stage == Plant.Stage.FINISHED:
            payload['recap_url'] = plant.get_recap_url()
        return JsonResponse(payload)
    if plant.growth_stage == Plant.Stage.FINISHED and changed:
        messages.success(request, f'{plant.name} is finished. Here is its growing story.')
        return redirect(plant.get_recap_url())
    messages.success(request, f'Growth stage updated to {plant.get_growth_stage_display()}.')
    return redirect(plant)


@login_required
@require_http_methods(['GET', 'POST'])
def plant_delete(request, pk):
    plant = _owned_plant(request, pk)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                plant.delete()
        except (ProtectedError, RestrictedError):
            error = 'This plant has care tasks or journal entries. Mark it Finished to keep its history.'
            if _wants_json(request):
                return JsonResponse({'error': error}, status=409)
            return render(request, 'my_plants/confirm_delete.html', {'plant': plant, 'error': error}, status=409)
        if _wants_json(request):
            return JsonResponse({'deleted': True})
        messages.success(request, f'{plant.name} was deleted.')
        return redirect('my_plants:list')
    return render(request, 'my_plants/confirm_delete.html', {'plant': plant})


@login_required
@require_GET
def plant_api(request):
    context = _list_context(request)
    if context['filter_form'].errors:
        return JsonResponse({'errors': context['filter_form'].errors.get_json_data()}, status=400)
    page = context['page_obj']
    return JsonResponse({
        'plants': [_serialize(plant) for plant in page], 'total': page.paginator.count,
        'page': page.number, 'pages': page.paginator.num_pages, 'stats': context['stats'],
    })


@login_required
@require_GET
def plant_detail_api(request, pk):
    plant = _owned_plant(request, pk)
    photos = list(plant.photos.without_image())
    for photo in photos:
        photo.plant = plant
    return JsonResponse({'plant': _serialize(plant), 'photos': [_serialize_photo(p) for p in photos]})


@login_required
@require_GET
def species_api(request):
    query = request.GET.get('q', '').strip()
    indoor = request.GET.get('indoor', '')
    if not 2 <= len(query) <= 120 or indoor not in ('', '0', '1'):
        return JsonResponse({'error': 'Enter 2–120 characters and a valid growing location.'}, status=400)
    try:
        results = search_species(query, indoor)
    except CatalogUnavailable as exc:
        return JsonResponse({'error': str(exc)}, status=503)
    return JsonResponse({'results': results, 'source': 'Perenual'})


@login_required
@require_POST
def check_in_create(request, pk):
    plant = _owned_plant(request, pk)
    form = CheckInForm(request.POST)
    if not form.is_valid():
        if _wants_json(request):
            return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
        return render(request, 'my_plants/detail.html', _detail_context(plant, check_in_form=form), status=400)
    check_in = form.save(commit=False)
    check_in.plant = plant
    check_in.save()
    if _wants_json(request):
        html = render_to_string('my_plants/_check_in.html', {'check_in': check_in, 'plant': plant}, request=request)
        return JsonResponse({'check_in': _serialize_check_in(check_in), 'html': html,
                             'count': plant.check_ins.count()}, status=201)
    messages.success(request, f'Saved: {check_in.get_condition_display()}.')
    return redirect(plant)


@login_required
@require_POST
def check_in_delete(request, pk, check_in_pk):
    plant = _owned_plant(request, pk)
    check_in = get_object_or_404(PlantCheckIn, pk=check_in_pk, plant=plant)
    check_in.delete()
    if _wants_json(request):
        return JsonResponse({'deleted': True, 'count': plant.check_ins.count()})
    messages.success(request, 'Check-in removed.')
    return redirect(plant)


@login_required
@require_GET
def photo_view(request, pk, photo_pk):
    """Serve a stored photo only to its owner. Content never changes, so it can be cached."""
    plant = _owned_plant(request, pk)
    photo = get_object_or_404(PlantPhoto, pk=photo_pk, plant=plant)
    response = HttpResponse(bytes(photo.image), content_type=photo.content_type)
    response['Cache-Control'] = 'private, max-age=31536000, immutable'
    response['Content-Disposition'] = f'inline; filename="plant-{plant.pk}-{photo.pk}.jpg"'
    return response


@login_required
@require_POST
def photo_add(request, pk):
    plant = _owned_plant(request, pk)
    form = PhotoForm(request.POST, request.FILES)
    if not form.is_valid():
        if _wants_json(request):
            return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
        return render(request, 'my_plants/detail.html', _detail_context(plant, photo_form=form), status=400)
    photo = _save_photo(plant, form, PlantPhoto.Kind.PROGRESS)
    if _wants_json(request):
        html = render_to_string('my_plants/_photo_tile.html', {'photo': photo, 'plant': plant}, request=request)
        return JsonResponse({'photo': _serialize_photo(photo), 'html': html, 'count': plant.photos.count()}, status=201)
    messages.success(request, 'Photo added to the diary.')
    return redirect(f'{plant.get_absolute_url()}#photo-diary')


@login_required
@require_POST
def photo_delete(request, pk, photo_pk):
    plant = _owned_plant(request, pk)
    get_object_or_404(PlantPhoto, pk=photo_pk, plant=plant).delete()
    if _wants_json(request):
        return JsonResponse({'deleted': True, 'count': plant.photos.count(), 'cover_photo_url': _cover_url(plant)})
    messages.success(request, 'Photo removed.')
    return redirect(f'{plant.get_absolute_url()}#photo-diary')


def _recap_context(plant):
    """Build the growing story from the photo diary: when each stage started and how long it lasted."""
    photos = list(plant.photos.without_image())
    for photo in photos:
        photo.plant = plant
    local_date = lambda dt: timezone.localtime(dt).date()  # noqa: E731
    order = [stage.value for stage in Plant.Stage]
    starts = {}
    for photo in photos:
        starts.setdefault(photo.stage, local_date(photo.created_at))
    starts.setdefault(plant.growth_stage, local_date(plant.updated_at))
    reached = sorted(starts, key=lambda s: (starts[s], order.index(s)))
    starts[reached[0]] = min(starts[reached[0]], plant.planted_on)
    finished = plant.growth_stage == Plant.Stage.FINISHED
    end = starts.get(Plant.Stage.FINISHED.value, timezone.localdate()) if finished else timezone.localdate()
    total_days = max((end - plant.planted_on).days, 0)

    segments = []
    for index, stage in enumerate(reached):
        if stage == Plant.Stage.FINISHED:
            continue
        until = starts[reached[index + 1]] if index + 1 < len(reached) else end
        days = max((until - starts[stage]).days, 0)
        segments.append({'stage': stage, 'label': Plant.Stage(stage).label, 'start': starts[stage],
                         'days': days, 'grow': max(days, 1)})
    chapters = [{'stage': stage, 'label': Plant.Stage(stage).label, 'start': starts[stage],
                 'day': max((starts[stage] - plant.planted_on).days, 0),
                 'photos': [p for p in photos if p.stage == stage]} for stage in reached]

    conditions = {row['condition']: row['n'] for row in plant.check_ins.values('condition').annotate(n=Count('pk'))}
    check_in_total = sum(conditions.values())
    condition_rows = [{'label': label, 'count': conditions.get(value, 0), 'value': value}
                      for value, label in PlantCheckIn.Condition.choices if conditions.get(value)]
    healthy = round(conditions.get(PlantCheckIn.Condition.NORMAL, 0) / check_in_total * 100) if check_in_total else None
    longest = max(segments, key=lambda s: s['days']) if segments else None
    return {
        'plant': plant, 'photos': photos, 'first_photo': photos[0] if photos else None,
        'last_photo': photos[-1] if len(photos) > 1 else None, 'cover': photos[-1] if photos else None,
        'segments': segments, 'chapters': chapters, 'total_days': total_days, 'finished': finished,
        'finished_on': starts.get(Plant.Stage.FINISHED.value) if finished else None,
        'stages_reached': len([s for s in reached if s != Plant.Stage.FINISHED]),
        'check_in_total': check_in_total, 'condition_rows': condition_rows, 'healthy_pct': healthy,
        'longest': longest,
    }


@login_required
@require_GET
def plant_recap(request, pk):
    return render(request, 'my_plants/recap.html', _recap_context(_owned_plant(request, pk)))
