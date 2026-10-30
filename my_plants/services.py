import json
from hashlib import sha256
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache


class CatalogUnavailable(Exception):
    pass


def search_species(query, indoor=''):
    """Read Perenual through the server; never expose its key to the browser."""
    api_key = settings.PERENUAL_API_KEY
    if not api_key:
        raise CatalogUnavailable('Plant lookup is unavailable. You can enter the species manually.')
    digest = sha256(f'{query.casefold()}:{indoor}'.encode()).hexdigest()
    cache_key = f'my_plants:species:{digest}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    params = {'key': api_key, 'q': query, 'page': 1}
    if indoor:
        params['indoor'] = indoor
    request = Request(
        'https://perenual.com/api/v2/species-list?' + urlencode(params),
        headers={'Accept': 'application/json', 'User-Agent': 'TerraPeer/1.0'},
    )
    try:
        with urlopen(request, timeout=8) as response:
            payload = json.load(response)
        if not isinstance(payload, dict) or not isinstance(payload.get('data'), list):
            raise ValueError('Invalid catalogue response')
        results = []
        for item in payload['data'][:30]:
            if not isinstance(item, dict):
                continue
            name = item.get('common_name')
            species_id = item.get('id')
            if not isinstance(name, str) or not name.strip() or not isinstance(species_id, int) or species_id < 1:
                continue
            scientific = item.get('scientific_name')
            results.append({
                'id': species_id, 'name': name[:160],
                'scientific_name': ', '.join(x for x in scientific if isinstance(x, str)) if isinstance(scientific, list) else '',
            })
    except (URLError, OSError, ValueError, TypeError) as exc:
        raise CatalogUnavailable('Plant lookup could not load. Try again or enter the species manually.') from exc
    cache.set(cache_key, results, 300)
    return results
