import io
import json
from datetime import timedelta
from unittest.mock import patch
from urllib.error import URLError

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import PlantForm
from .models import Plant, PlantCheckIn
from .services import CatalogUnavailable, search_species


class PlantTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user('gardener', password='Test-pass-2026')
        cls.other = get_user_model().objects.create_user('other', password='Test-pass-2026')
        cls.plant = Plant.objects.create(owner=cls.owner, name='Balcony tomato', species_name='Tomato')
        cls.other_plant = Plant.objects.create(owner=cls.other, name='Private basil', species_name='Basil')

    def setUp(self):
        self.client.force_login(self.owner)
        self.data = {
            'name': 'Kitchen basil', 'species_name': 'Basil',
            'planted_on': timezone.localdate().isoformat(), 'growth_stage': 'growing', 'notes': '',
        }

    def url(self, name, plant=None):
        return reverse(f'my_plants:{name}', args=[(plant or self.plant).pk])

    def test_all_private_pages_require_login(self):
        self.client.logout()
        urls = [reverse(f'my_plants:{name}') for name in ['list', 'create', 'api', 'fragment', 'species']]
        urls += [self.url(name) for name in ['detail', 'detail_api', 'edit', 'delete', 'stage']]
        for url in urls:
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), reverse('login') + '?next=' + url, fetch_redirect_response=False)

    def test_list_and_json_never_include_other_users_plants(self):
        self.assertContains(self.client.get(reverse('my_plants:list')), self.plant.name)
        self.assertNotContains(self.client.get(reverse('my_plants:list')), self.other_plant.name)
        data = self.client.get(reverse('my_plants:api')).json()
        self.assertEqual([plant['id'] for plant in data['plants']], [self.plant.pk])
        self.assertEqual(data['stats']['total'], 1)
        self.assertNotIn('owner', data['plants'][0])

    def test_empty_garden_has_working_first_plant_link(self):
        self.plant.delete()
        response = self.client.get(reverse('my_plants:list'))
        self.assertContains(response, 'Every garden starts with one plant.')
        self.assertContains(response, reverse('my_plants:create'))

    def test_private_object_urls_cannot_be_used_by_another_user(self):
        self.client.force_login(self.other)
        for name in ['detail', 'detail_api', 'edit', 'delete']:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(self.url(name)).status_code, 404)
        for name in ['edit', 'delete', 'stage']:
            with self.subTest(name=name):
                self.assertEqual(self.client.post(self.url(name), self.data).status_code, 404)
        self.plant.refresh_from_db()
        self.assertEqual(self.plant.name, 'Balcony tomato')

    def test_create_sets_owner_from_session_and_returns_json(self):
        data = {**self.data, 'owner': self.other.pk, 'status': 'finished'}
        response = self.client.post(reverse('my_plants:create'), data, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 201)
        plant = Plant.objects.get(pk=response.json()['plant']['id'])
        self.assertEqual(plant.owner, self.owner)
        self.assertEqual(plant.status, 'active')

    def test_create_with_no_js_redirects_to_detail(self):
        response = self.client.post(reverse('my_plants:create'), self.data)
        plant = Plant.objects.get(name='Kitchen basil')
        self.assertRedirects(response, plant.get_absolute_url())

    def test_future_date_and_invalid_stage_are_rejected(self):
        for field, value in [('planted_on', (timezone.localdate() + timedelta(days=1)).isoformat()),
                             ('growth_stage', 'invented'), ('name', ''), ('species_name', ''),
                             ('notes', 'x' * 2001), ('perenual_species_id', 0)]:
            with self.subTest(field=field):
                response = self.client.post(reverse('my_plants:create'), {**self.data, field: value}, HTTP_ACCEPT='application/json')
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json()['errors'])
        self.assertEqual(Plant.objects.for_user(self.owner).count(), 1)

    def test_invalid_html_form_keeps_entered_values(self):
        response = self.client.post(reverse('my_plants:create'), {**self.data, 'species_name': ''})
        self.assertContains(response, 'Kitchen basil', status_code=400)
        self.assertContains(response, 'This field is required.', status_code=400)

    def test_get_forms_and_details_render(self):
        for url in [reverse('my_plants:create'), self.url('edit'), self.url('detail'), self.url('delete')]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(self.url('detail_api')).json()['plant']['name'], self.plant.name)

    def test_update_preserves_id_and_owner(self):
        response = self.client.post(self.url('edit'), {**self.data, 'owner': self.other.pk}, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.plant.refresh_from_db()
        self.assertEqual(self.plant.name, 'Kitchen basil')
        self.assertEqual(self.plant.owner, self.owner)
        self.assertEqual(response.json()['plant']['id'], self.plant.pk)

    def test_invalid_update_does_not_change_database(self):
        response = self.client.post(self.url('edit'), {**self.data, 'growth_stage': 'invalid'}, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 400)
        self.plant.refresh_from_db()
        self.assertEqual(self.plant.name, 'Balcony tomato')

    def test_finished_status_is_derived_and_reopening_is_consistent(self):
        for stage, status in [('finished', 'finished'), ('flowering', 'active')]:
            response = self.client.post(self.url('stage'), {'growth_stage': stage}, HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 200)
            self.plant.refresh_from_db()
            self.assertEqual(self.plant.status, status)
            self.assertEqual(response.json()['plant']['status'], status)
        self.assertEqual(self.client.get(self.url('stage')).status_code, 405)

    def test_invalid_stage_has_html_and_json_errors(self):
        for accept in ['text/html', 'application/json']:
            self.assertEqual(self.client.post(self.url('stage'), {'growth_stage': 'unknown'}, HTTP_ACCEPT=accept).status_code, 400)

    def test_stage_and_edit_html_success_redirect(self):
        self.assertRedirects(self.client.post(self.url('stage'), {'growth_stage': 'flowering'}), self.plant.get_absolute_url())
        self.assertRedirects(self.client.post(self.url('edit'), self.data), self.plant.get_absolute_url())

    def test_delete_requires_post_and_preserves_plant_on_confirmation_page(self):
        self.client.get(self.url('delete'))
        self.assertTrue(Plant.objects.filter(pk=self.plant.pk).exists())
        response = self.client.post(self.url('delete'), HTTP_ACCEPT='application/json')
        self.assertEqual(response.json(), {'deleted': True})
        self.assertFalse(Plant.objects.filter(pk=self.plant.pk).exists())

    def test_html_delete_redirects(self):
        self.assertRedirects(self.client.post(self.url('delete')), reverse('my_plants:list'))

    def test_linked_record_protection_returns_actionable_conflict(self):
        with patch.object(Plant, 'delete', side_effect=ProtectedError('linked', {self.plant})):
            for accept in ['text/html', 'application/json']:
                response = self.client.post(self.url('delete'), HTTP_ACCEPT=accept)
                self.assertEqual(response.status_code, 409)
        self.assertTrue(Plant.objects.filter(pk=self.plant.pk).exists())

    def test_csrf_required_for_mutations(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        for url in [reverse('my_plants:create'), self.url('edit'), self.url('delete'), self.url('stage')]:
            with self.subTest(url=url):
                self.assertEqual(client.post(url, self.data).status_code, 403)
        client.get(reverse('my_plants:create'))
        response = client.post(reverse('my_plants:create'), self.data,
                               HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertEqual(response.status_code, 302)

    def test_filters_combine_and_stats_remain_garden_wide(self):
        Plant.objects.create(owner=self.owner, name='Window basil', species_name='Basil', growth_stage='finished')
        response = self.client.get(reverse('my_plants:api'), {'q': 'basil', 'stage': 'finished', 'status': 'finished'})
        self.assertEqual(response.json()['total'], 1)
        self.assertEqual(response.json()['stats']['total'], 2)
        self.assertEqual(response.json()['plants'][0]['name'], 'Window basil')
        self.assertEqual(self.client.get(reverse('my_plants:api'), {'status': 'active'}).json()['total'], 1)
        self.assertEqual(self.client.get(reverse('my_plants:api'), {'q': 'not found'}).json()['total'], 0)
        self.assertEqual(self.client.get(reverse('my_plants:api'), {'stage': 'invalid'}).status_code, 400)

    def test_pagination_and_fragment(self):
        Plant.objects.bulk_create([Plant(owner=self.owner, name=f'Seedling {i}', species_name='Tomato') for i in range(13)])
        data = self.client.get(reverse('my_plants:api'), {'page': 2}).json()
        self.assertEqual(data['total'], 14)
        self.assertEqual(len(data['plants']), 2)
        response = self.client.get(reverse('my_plants:fragment'), {'q': 'Balcony'})
        self.assertContains(response, self.plant.name)
        self.assertNotContains(response, '<html')

    def test_user_text_is_escaped_in_ajax_fragment(self):
        self.plant.name = '<script>alert(1)</script>'
        self.plant.save()
        response = self.client.get(reverse('my_plants:fragment'))
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;')

    def test_model_validation_and_stage_constraint(self):
        self.plant.planted_on = timezone.localdate() + timedelta(days=1)
        with self.assertRaises(ValidationError):
            self.plant.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Plant.objects.filter(pk=self.plant.pk).update(growth_stage='invalid')

    def test_days_and_string_representation(self):
        self.plant.planted_on = timezone.localdate() - timedelta(days=5)
        self.assertEqual(self.plant.days_growing, 5)
        self.assertEqual(str(self.plant), 'Balcony tomato')
        self.assertEqual(Plant.objects.for_user(self.owner).active().count(), 1)

    def test_login_returns_to_private_page_without_allowing_external_redirect(self):
        self.client.logout()
        for target, expected in [('/my-plants/', '/my-plants/'), ('https://evil.example/', reverse('show_main'))]:
            response = self.client.post(reverse('login'), {'username': 'gardener', 'password': 'Test-pass-2026', 'next': target})
            self.assertRedirects(response, expected)
            self.client.logout()


@override_settings(PERENUAL_API_KEY='unit-test-key')
class SpeciesLookupTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user('api-user')
        self.client.force_login(self.user)

    @patch('my_plants.services.urlopen')
    def test_search_forwards_allowed_filters_and_caches_results(self, upstream):
        upstream.return_value = io.StringIO(json.dumps({'data': [
            {'id': 9, 'common_name': 'Basil', 'scientific_name': ['Ocimum basilicum']},
            {'id': 10, 'common_name': '', 'scientific_name': []},
        ]}))
        response = self.client.get(reverse('my_plants:species'), {'q': 'basil', 'indoor': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['results'][0]['name'], 'Basil')
        self.assertNotContains(response, 'unit-test-key')
        request = upstream.call_args.args[0]
        self.assertIn('indoor=1', request.full_url)
        self.assertIn('q=basil', request.full_url)
        self.assertEqual(len(search_species('basil', '1')), 1)
        self.assertEqual(upstream.call_count, 1)

    @override_settings(PERENUAL_API_KEY='')
    @patch('my_plants.services.urlopen')
    def test_missing_key_keeps_manual_entry_available(self, upstream):
        response = self.client.get(reverse('my_plants:species'), {'q': 'basil'})
        self.assertEqual(response.status_code, 503)
        self.assertIn('manually', response.json()['error'])
        upstream.assert_not_called()
        self.assertEqual(self.client.get(reverse('my_plants:create')).status_code, 200)

    @patch('my_plants.services.urlopen', side_effect=URLError('provider failure'))
    def test_provider_failure_is_handled_without_disclosing_request(self, upstream):
        response = self.client.get(reverse('my_plants:species'), {'q': 'basil'})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('unit-test-key', response.content.decode())

    @patch('my_plants.services.urlopen')
    def test_invalid_provider_response_is_handled(self, upstream):
        for payload in ['not json', '[]', '{"data": null}']:
            with self.subTest(payload=payload):
                upstream.return_value = io.StringIO(payload)
                with self.assertRaises(CatalogUnavailable):
                    search_species('basil')

    @patch('my_plants.services.urlopen')
    def test_bad_queries_do_not_call_provider(self, upstream):
        for params in [{'q': 'a'}, {'q': 'basil', 'indoor': 'unexpected'}, {'q': 'x' * 121}]:
            self.assertEqual(self.client.get(reverse('my_plants:species'), params).status_code, 400)
        upstream.assert_not_called()



class PlantListExtrasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user('sorter', password='Test-pass-2026')
        today = timezone.localdate()
        cls.old = Plant.objects.create(owner=cls.owner, name='Aloe', species_name='Aloe vera',
                                       planted_on=today - timedelta(days=200), growth_stage='flowering')
        cls.new = Plant.objects.create(owner=cls.owner, name='Zinnia', species_name='Zinnia',
                                       planted_on=today - timedelta(days=3), growth_stage='finished')

    def setUp(self):
        self.client.force_login(self.owner)

    def names(self, **params):
        return [p['name'] for p in self.client.get(reverse('my_plants:api'), params).json()['plants']]

    def test_sort_options(self):
        self.assertEqual(self.names(sort='name'), ['Aloe', 'Zinnia'])
        self.assertEqual(self.names(sort='planted'), ['Aloe', 'Zinnia'])
        self.assertEqual(self.names(sort='newest'), ['Zinnia', 'Aloe'])
        self.assertEqual(self.names(sort='oldest'), ['Aloe', 'Zinnia'])
        self.assertEqual(self.client.get(reverse('my_plants:api'), {'sort': 'random'}).status_code, 400)

    def test_stats_summarise_the_whole_garden(self):
        stats = self.client.get(reverse('my_plants:api'), {'q': 'Aloe'}).json()['stats']
        self.assertEqual((stats['total'], stats['active'], stats['blooming'], stats['finished']), (2, 1, 1, 1))

    def test_list_uses_bootstrap_layout_and_navbar_link(self):
        response = self.client.get(reverse('my_plants:list'))
        self.assertContains(response, 'bootstrap.min.css')
        self.assertContains(response, 'row-cols-lg-3')
        self.assertContains(response, 'aria-current="page">My Plants')

    def test_stage_json_returns_stepper_state(self):
        response = self.client.post(reverse('my_plants:stage', args=[self.old.pk]), {'growth_stage': 'harvesting'},
                                    HTTP_ACCEPT='application/json')
        states = {step['value']: step['state'] for step in response.json()['steps']}
        self.assertEqual(states, {'growing': 'done', 'flowering': 'done', 'fruiting': 'done',
                                  'harvesting': 'current', 'finished': 'todo'})


class CheckInTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user('owner', password='Test-pass-2026')
        cls.other = User.objects.create_user('intruder', password='Test-pass-2026')
        cls.plant = Plant.objects.create(owner=cls.owner, name='Tomato 1', species_name='Tomato')

    def setUp(self):
        self.client.force_login(self.owner)
        self.create_url = reverse('my_plants:check_in_create', args=[self.plant.pk])

    def test_create_with_json_returns_rendered_row(self):
        response = self.client.post(self.create_url, {'condition': 'wilting', 'note': 'Hot afternoon'},
                                    HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['check_in']['condition_label'], 'Wilting')
        self.assertTrue(data['check_in']['needs_attention'])
        self.assertIn('Hot afternoon', data['html'])
        self.assertEqual(data['count'], 1)

    def test_create_without_js_redirects_and_shows_on_detail(self):
        response = self.client.post(self.create_url, {'condition': 'normal'})
        self.assertRedirects(response, self.plant.get_absolute_url())
        self.assertContains(self.client.get(self.plant.get_absolute_url()), 'Growing normally')

    def test_invalid_condition_is_rejected(self):
        for accept in ['application/json', 'text/html']:
            response = self.client.post(self.create_url, {'condition': 'on fire'}, HTTP_ACCEPT=accept)
            self.assertEqual(response.status_code, 400)
        self.assertFalse(PlantCheckIn.objects.exists())

    def test_other_users_cannot_add_or_delete(self):
        check_in = PlantCheckIn.objects.create(plant=self.plant, condition='normal')
        delete_url = reverse('my_plants:check_in_delete', args=[self.plant.pk, check_in.pk])
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.create_url, {'condition': 'pests'}).status_code, 404)
        self.assertEqual(self.client.post(delete_url).status_code, 404)
        self.assertTrue(PlantCheckIn.objects.filter(pk=check_in.pk).exists())

    def test_check_in_must_belong_to_the_plant_in_the_url(self):
        second = Plant.objects.create(owner=self.owner, name='Basil', species_name='Basil')
        check_in = PlantCheckIn.objects.create(plant=second, condition='normal')
        url = reverse('my_plants:check_in_delete', args=[self.plant.pk, check_in.pk])
        self.assertEqual(self.client.post(url).status_code, 404)

    def test_delete_and_login_and_method_rules(self):
        check_in = PlantCheckIn.objects.create(plant=self.plant, condition='dry_soil')
        delete_url = reverse('my_plants:check_in_delete', args=[self.plant.pk, check_in.pk])
        self.assertEqual(self.client.get(delete_url).status_code, 405)
        self.assertEqual(self.client.post(delete_url, HTTP_ACCEPT='application/json').json(), {'deleted': True, 'count': 0})
        self.client.logout()
        self.assertRedirects(self.client.post(self.create_url, {'condition': 'normal'}),
                             reverse('login') + '?next=' + self.create_url, fetch_redirect_response=False)

    def test_deleting_plant_removes_its_check_ins(self):
        PlantCheckIn.objects.create(plant=self.plant, condition='normal')
        self.client.post(reverse('my_plants:delete', args=[self.plant.pk]))
        self.assertFalse(PlantCheckIn.objects.exists())
        self.assertEqual(str(PlantCheckIn(plant=Plant(name='X'), condition='pests')), 'X · Pests spotted')
