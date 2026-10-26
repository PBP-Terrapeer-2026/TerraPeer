from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from .models import CareTask, Plant


@transaction.atomic
def complete_task(task_id, owner):
    task = (
        CareTask.objects.select_for_update()
        .select_related("plant__garden")
        .get(pk=task_id, plant__garden__owner=owner)
    )
    if task.status == "Completed":
        return task, None, False
    # Conditional update adds a second guard against duplicate completion.
    changed = CareTask.objects.filter(pk=task.pk, status="Pending").update(
        status="Completed", completed_at=timezone.now()
    )
    if not changed:
        return task, None, False
    task.refresh_from_db()
    following = None
    active = Plant.objects.filter(pk=task.plant_id, status="Active").exists()
    if task.repeat_every and active:
        date = task.due_date + timedelta(days=task.repeat_every)
        following = CareTask.objects.create(
            plant=task.plant,
            title=task.title,
            action_type=task.action_type,
            due_date=date,
            repeat_every=task.repeat_every,
            instructions=task.instructions,
            previous=task,
        )
    return task, following, True
