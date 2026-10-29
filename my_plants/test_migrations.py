from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class DailyCheckInMigrationTests(TransactionTestCase):
    def test_existing_same_day_history_is_preserved(self):
        old_target = [('my_plants', '0003_plantphoto')]
        new_target = [('my_plants', '0004_daily_check_in_and_request_quota')]
        executor = MigrationExecutor(connection)
        executor.migrate(old_target)
        try:
            old = executor.loader.project_state(old_target).apps
            user = old.get_model('auth', 'User').objects.create(username='legacy-history')
            plant = old.get_model('my_plants', 'Plant').objects.create(owner_id=user.pk, name='Legacy', species_name='Mint')
            CheckIn = old.get_model('my_plants', 'PlantCheckIn')
            first = CheckIn.objects.create(plant_id=plant.pk, condition='normal')
            second = CheckIn.objects.create(plant_id=plant.pk, condition='wilting')
            executor = MigrationExecutor(connection)
            executor.migrate(new_target)
            new = executor.loader.project_state(new_target).apps
            records = new.get_model('my_plants', 'PlantCheckIn').objects.filter(plant_id=plant.pk)
            self.assertEqual(records.count(), 2)
            self.assertIsNone(records.get(pk=first.pk).checked_on)
            self.assertIsNotNone(records.get(pk=second.pk).checked_on)
        finally:
            MigrationExecutor(connection).migrate(new_target)
