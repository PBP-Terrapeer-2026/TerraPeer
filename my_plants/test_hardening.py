"""Regression and security cases added before the corresponding implementation."""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Plant, PlantCheckIn, PlantPhoto
from .tests import photo_upload


class MyPlantsHardeningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user('hardening-owner')
        cls.other = get_user_model().objects.create_user('hardening-other')
        cls.plant = Plant.objects.create(owner=cls.owner, name='Tomato', species_name='Tomato')
        cls.second = Plant.objects.create(owner=cls.owner, name='Basil', species_name='Basil')
        cls.private = Plant.objects.create(owner=cls.other, name='Mint', species_name='Mint')

    def setUp(self):
        self.client.force_login(self.owner)

    def post(self, route_name, plant=None, **data):
        return self.client.post(reverse(f'my_plants:{route_name}', args=[(plant or self.plant).pk]),
                                data, HTTP_ACCEPT='application/json')

    def test_daily_check_in_is_per_plant_and_per_owner(self):
        self.assertEqual(self.post('check_in_create', condition='normal').status_code, 201)
        self.assertEqual(self.post('check_in_create', self.second, condition='normal').status_code, 201)
        self.client.force_login(self.other)
        self.assertEqual(self.post('check_in_create', self.private, condition='normal').status_code, 201)

    def test_duplicate_check_in_returns_actionable_json(self):
        self.post('check_in_create', condition='normal')
        response = self.post('check_in_create', condition='pests')
        self.assertEqual(response.status_code, 409)
        self.assertIn('today', response.json()['error'])
        self.assertEqual(self.plant.check_ins.count(), 1)

    def test_daily_rule_is_enforced_by_database(self):
        PlantCheckIn.objects.create(plant=self.plant, condition='normal')
        with self.assertRaises(IntegrityError), transaction.atomic():
            PlantCheckIn.objects.create(plant=self.plant, condition='wilting')

    def test_check_in_is_allowed_on_next_calendar_day(self):
        self.post('check_in_create', condition='normal')
        tomorrow = timezone.localdate() + timedelta(days=1)
        with patch('my_plants.views.timezone.localdate', return_value=tomorrow):
            self.assertEqual(self.post('check_in_create', condition='normal').status_code, 201)

    def edit_data(self):
        return {'name': 'Tomato edited', 'species_name': 'Tomato',
                'planted_on': self.plant.planted_on.isoformat(), 'growth_stage': 'flowering'}

    def test_edit_cannot_bypass_required_stage_photo(self):
        response = self.post('edit', **self.edit_data())
        self.assertEqual(response.status_code, 400)
        self.assertIn('photo', response.json()['errors'])
        self.plant.refresh_from_db()
        self.assertEqual(self.plant.growth_stage, 'growing')

    def test_edit_stage_photo_is_recorded_as_stage_not_progress(self):
        self.assertEqual(self.post('edit', **self.edit_data(), photo=photo_upload()).status_code, 200)
        photo = self.plant.photos.get()
        self.assertEqual((photo.stage, photo.kind), ('flowering', 'stage'))

    def bulk(self, ids):
        return self.client.post(reverse('my_plants:bulk_delete'), {'plant_ids': ids},
                                HTTP_ACCEPT='application/json')

    def test_bulk_delete_is_all_or_nothing_for_ownership(self):
        response = self.bulk([self.plant.pk, self.private.pk])
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Plant.objects.filter(pk=self.plant.pk).exists())

    def test_bulk_delete_rejects_invalid_or_oversized_selection(self):
        for ids in [[], ['bad'], ['0'], list(range(1, 52))]:
            self.assertEqual(self.bulk(ids).status_code, 400)

    def test_bulk_delete_removes_selected_owned_plants_only(self):
        response = self.bulk([self.plant.pk, self.second.pk])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['deleted_count'], 2)
        self.assertTrue(Plant.objects.filter(pk=self.private.pk).exists())

    def test_bulk_delete_protected_record_rolls_back_whole_selection(self):
        from django.db.models.deletion import ProtectedError
        original = Plant.delete
        def delete(plant, *args, **kwargs):
            if plant.pk == self.second.pk:
                raise ProtectedError('linked', {plant})
            return original(plant, *args, **kwargs)
        with patch.object(Plant, 'delete', delete):
            self.assertEqual(self.bulk([self.plant.pk, self.second.pk]).status_code, 409)
        self.assertEqual(Plant.objects.for_user(self.owner).count(), 2)

    def test_advanced_filters_use_latest_condition_and_date_range(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        Plant.objects.filter(pk=self.second.pk).update(planted_on=yesterday)
        old = PlantCheckIn.objects.create(plant=self.plant, condition='pests', checked_on=yesterday)
        PlantCheckIn.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=1))
        PlantCheckIn.objects.create(plant=self.plant, condition='normal')
        PlantCheckIn.objects.create(plant=self.second, condition='wilting')
        response = self.client.get(reverse('my_plants:api'), {'health': 'attention', 'planted_to': yesterday})
        self.assertEqual([p['id'] for p in response.json()['plants']], [self.second.pk])
        response = self.client.get(reverse('my_plants:api'), {'health': 'normal'})
        self.assertEqual([p['id'] for p in response.json()['plants']], [self.plant.pk])

    def test_invalid_date_interval_is_rejected(self):
        today = timezone.localdate()
        response = self.client.get(reverse('my_plants:api'),
                                   {'planted_from': today, 'planted_to': today - timedelta(days=1)})
        self.assertEqual(response.status_code, 400)

    def test_api_query_count_does_not_grow_per_plant(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        url = reverse('my_plants:api')
        with CaptureQueriesContext(connection) as small:
            self.client.get(url)
        for i in range(8):
            plant = Plant.objects.create(owner=self.owner, name=f'Plant {i}', species_name='Mint')
            PlantPhoto.objects.create(plant=plant, image=b'x', width=1, height=1, stage='growing')
        with CaptureQueriesContext(connection) as large:
            self.client.get(url)
        self.assertEqual(len(small), len(large))

    def test_species_requests_are_throttled_per_account(self):
        url = reverse('my_plants:species')
        with patch('my_plants.views.search_species', return_value=[]):
            for _ in range(10):
                self.assertEqual(self.client.get(url, {'q': 'tomato'}).status_code, 200)
            response = self.client.get(url, {'q': 'tomato'})
            self.assertEqual(response.status_code, 429)
            self.assertGreater(int(response['Retry-After']), 0)
            self.client.force_login(self.other)
            self.assertEqual(self.client.get(url, {'q': 'tomato'}).status_code, 200)

    def test_bulk_endpoint_keeps_csrf_and_method_protection(self):
        from django.test import Client
        url = reverse('my_plants:bulk_delete')
        self.assertEqual(self.client.get(url).status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.owner)
        self.assertEqual(strict.post(url, {'plant_ids': [self.plant.pk]}).status_code, 403)

    def test_quota_resets_after_window_and_never_trusts_forwarded_ip(self):
        url = reverse('my_plants:species')
        with patch('my_plants.security.time.time', return_value=1200), patch('my_plants.views.search_species', return_value=[]):
            for _ in range(10):
                self.client.get(url, {'q': 'tomato'})
            response = self.client.get(url, {'q': 'tomato'}, HTTP_X_FORWARDED_FOR='a-different-address')
            self.assertEqual(response.status_code, 429)
        with patch('my_plants.security.time.time', return_value=1260), patch('my_plants.views.search_species', return_value=[]):
            self.assertEqual(self.client.get(url, {'q': 'tomato'}).status_code, 200)

    def test_mutation_quota_has_json_and_html_feedback(self):
        from .models import RequestQuota
        import time
        RequestQuota.objects.create(user=self.owner, scope='write', window=int(time.time()) // 60, hits=30)
        json_response = self.post('check_in_create', condition='normal')
        self.assertEqual(json_response.status_code, 429)
        self.assertIn('wait', json_response.json()['error'])
        html_response = self.client.post(reverse('my_plants:check_in_create', args=[self.plant.pk]), {'condition': 'normal'})
        self.assertEqual(html_response.status_code, 429)
        self.assertIn('wait', html_response.content.decode())
        self.assertEqual(self.client.get(reverse('my_plants:edit', args=[self.plant.pk])).status_code, 200)

    def test_health_none_filter_and_empty_interval(self):
        PlantCheckIn.objects.create(plant=self.plant, condition='normal')
        response = self.client.get(reverse('my_plants:api'), {'health': 'none', 'planted_from': timezone.localdate()})
        self.assertEqual([p['id'] for p in response.json()['plants']], [self.second.pk])

    def test_daily_duplicate_html_shows_feedback_and_keeps_note(self):
        self.post('check_in_create', condition='normal')
        response = self.client.post(reverse('my_plants:check_in_create', args=[self.plant.pk]),
                                    {'condition': 'pests', 'note': 'Keep this note'})
        self.assertContains(response, 'already saved a check-in', status_code=409)
        self.assertContains(response, 'Keep this note', status_code=409)

    def test_bulk_delete_html_fallback(self):
        url = reverse('my_plants:bulk_delete')
        self.assertContains(self.client.post(url, {}), 'Select between', status_code=400)
        self.assertRedirects(self.client.post(url, {'plant_ids': [self.plant.pk]}), reverse('my_plants:list'))
