from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone
from my_plants.models import Plant
from plant_care.models import CareTask


class Command(BaseCommand):
    help = "Add optional sample plants/tasks for an existing user; never create fake weather locations."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)

    def handle(self, *args, **options):
        user = get_user_model().objects.filter(username=options["username"]).first()
        if not user:
            raise CommandError(
                "Create this user first: python manage.py createsuperuser"
            )
        for name in ["Peppermint", "Tomato", "Basil"]:
            plant = Plant.objects.filter(
                owner=user, name=name, notes="Optional Plant Care sample"
            ).first()
            if plant is None:
                plant = Plant.objects.create(
                    owner=user,
                    name=name,
                    species_name=name,
                    notes="Optional Plant Care sample",
                )
            if name == "Peppermint":
                mint = plant
        if not mint.care_tasks.exists():
            for action, title, offset, interval in [
                ("Watering", "Check soil moisture", -1, 3),
                ("Inspection", "Check leaf condition", 0, None),
                ("Fertilizing", "Feed with diluted fertilizer", 3, 7),
            ]:
                CareTask.objects.create(
                    plant=mint,
                    action_type=action,
                    title=title,
                    due_date=timezone.localdate() + timedelta(days=offset),
                    repeat_every=interval,
                    instructions="Observe the plant before deciding what care it needs.",
                )
        self.stdout.write(
            self.style.SUCCESS(
                "Sample tasks ready at /plant-care/. Choose a real Garden Setup space for weather."
            )
        )
