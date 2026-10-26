from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from care.models import GardenSpace, Plant, CareTask


class Command(BaseCommand):
    help = (
        "Create a small sample garden for an EXISTING user; does not reset their data."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)

    def handle(self, *args, **options):
        user = get_user_model().objects.filter(username=options["username"]).first()
        if not user:
            raise CommandError(
                "Create this user first: python manage.py createsuperuser"
            )
        garden, _ = GardenSpace.objects.get_or_create(
            owner=user,
            name="My Balcony",
            defaults={"location": "Depok", "latitude": -6.4025, "longitude": 106.7942},
        )
        mint, _ = Plant.objects.get_or_create(
            garden=garden, name="Peppermint", defaults={"pot": "Pot B", "image": "mint"}
        )
        Plant.objects.get_or_create(
            garden=garden, name="Tomato", defaults={"pot": "Pot A", "image": "tomato"}
        )
        Plant.objects.get_or_create(
            garden=garden, name="Basil", defaults={"pot": "Pot C", "image": "mint"}
        )
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
                    due_date=mint.today + timedelta(days=offset),
                    repeat_every=interval,
                    instructions="Observe the plant before deciding what care it needs.",
                )
        self.stdout.write(
            self.style.SUCCESS(
                "Sample garden ready. Sign in at /login/, then open /plant-care/."
            )
        )
