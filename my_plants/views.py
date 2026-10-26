from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError, RestrictedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import PlantFilterForm, PlantForm, StageForm
from .models import Plant
from .services import CatalogUnavailable, search_species

PAGE_SIZE = 12


def _wants_json(request):
    return 'application/json' in request.headers.get('Accept', '')


def _owned_plant(request, pk):
    """Every private view goes through here, so a plant ID from another account is a 404."""
    return get_object_or_404(Plant.objects.for_user(request.user), pk=pk)


def _serialize(plant):
    return {
        'id': plant.pk, 'name': plant.name, 'species_name': plant.species_name,
        'planted_on': plant.planted_on.isoformat(), 'days_growing': plant.days_growing,
        'growth_stage': plant.growth_stage, 'growth_stage_label': plant.get_growth_stage_display(),
        'status': plant.status, 'notes': plant.notes, 'perenual_species_id': plant.perenual_species_id,
        'url': plant.get_absolute_url(),
    }


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
    plants = owned
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


def _detail_context(plant, stage_form=None):
    return {'plant': plant, 'stage_form': stage_form or StageForm(instance=plant), 'stage_steps': _stage_steps(plant)}


@login_required
@require_GET
def plant_detail(request, pk):
    return render(request, 'my_plants/detail.html', _detail_context(_owned_plant(request, pk)))


@login_required
@require_http_methods(['GET', 'POST'])
def plant_create(request):
    form = PlantForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        plant = form.save(commit=False)
        plant.owner = request.user
        plant.save()
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
    form = PlantForm(request.POST if request.method == 'POST' else None, instance=plant)
    if request.method == 'POST' and form.is_valid():
        plant = form.save()
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
    form = StageForm(request.POST, instance=plant)
    if not form.is_valid():
        if _wants_json(request):
            return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
        plant.refresh_from_db()
        return render(request, 'my_plants/detail.html', _detail_context(plant, form), status=400)
    plant = form.save()
    if _wants_json(request):
        return JsonResponse({'plant': _serialize(plant), 'steps': _stage_steps(plant)})
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
    return JsonResponse({'plant': _serialize(_owned_plant(request, pk))})


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
