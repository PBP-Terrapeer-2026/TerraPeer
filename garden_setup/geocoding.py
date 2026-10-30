import json
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://geocoding-api.open-meteo.com/v1"

class GeocodingServiceError(Exception):
    """Error ketika layanan lokasi tidak tersedia."""

def _fetch_json(endpoint, parameters):
    url = f"{BASE_URL}/{endpoint}?{urlencode(parameters)}"

    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "TerraPeer/1.0",
        },
    )

    try:
        with urlopen(request, timeout=5) as response:
            data = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise GeocodingServiceError(
            "Location service is temporarily unavailable."
        ) from exc

    if not isinstance(data, dict) or data.get("error"):
        raise GeocodingServiceError(
            "Location service returned an invalid response."
        )

    return data


def _normalize_location(item):
    """Mengubah respons API menjadi data lokasi TerraPeer."""

    try:
        location_id = int(item["id"])
        latitude = Decimal(str(item["latitude"]))
        longitude = Decimal(str(item["longitude"]))
        name = str(item["name"]).strip()
        country = str(item["country"]).strip()
        timezone = str(item["timezone"]).strip()

        if not (0 < location_id <= 9223372036854775807):
            return None
        if not latitude.is_finite() or not longitude.is_finite():
            return None
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            return None
        if not name or not country or not timezone:
            return None

        return {
            "id": location_id,
            "name": name,
            "region": str(item.get("admin1") or "").strip(),
            "country": country,
            "latitude": str(latitude.quantize(Decimal("0.000001"))),
            "longitude": str(longitude.quantize(Decimal("0.000001"))),
            "timezone": timezone,
        }

    except (KeyError, TypeError, ValueError, InvalidOperation, AttributeError):
        return None

def search_locations(name):
    """Mencari lokasi berdasarkan nama kota."""

    name = name.strip()
    if len(name) < 2:
        return []

    data = _fetch_json(
        "search",
        {
            "name": name[:80],
            "count": 6,
            "language": "en",
            "format": "json",
        },
    )

    results = data.get("results") or []

    if not isinstance(results, list):
        raise GeocodingServiceError("Invalid location search response.")

    locations = []

    for item in results:
        if isinstance(item, dict):
            location = _normalize_location(item)
            if location is not None:
                locations.append(location)

    return locations

def get_location_by_id(location_id):
    """Memverifikasi lokasi berdasarkan ID Open-Meteo."""

    location_id = int(location_id)

    if not (0 < location_id <= 9223372036854775807):
        return None

    data = _fetch_json("get", {"id": location_id},)
    location = _normalize_location(data)

    if location is None:
        return None

    if location["id"] != location_id:
        return None

    return location