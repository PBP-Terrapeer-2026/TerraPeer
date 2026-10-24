"""Open-Meteo daily forecast: timeout, cache, timezone, missing values."""

from datetime import timedelta
from zoneinfo import ZoneInfo
import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


class ForecastUnavailable(Exception):
    pass


def condition(code):
    if code == 0:
        return "Sunny", "sunny", "sun"
    if code in (1, 2):
        return "Partly cloudy", "mixed", "cloudsun"
    if code == 3:
        return "Cloudy", "cloudy", "cloud"
    if code in (45, 48):
        return "Foggy", "cloudy", "cloud"
    if code in (51, 53, 55, 56, 57):
        return "Drizzle", "rainy", "rain"
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "Rainy", "rainy", "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "Snow", "cloudy", "cloud"
    if code in (95, 96, 99):
        return "Thunderstorm", "rainy", "rain"
    return "Condition unavailable", "cloudy", "cloud"


def forecast(garden):
    if garden.latitude is None or garden.longitude is None:
        return {"state": "no-location", "days": []}
    today = timezone.localdate(timezone=ZoneInfo(garden.timezone_name))
    if settings.WEATHER_DEMO:
        days = []
        for i, (code, lo, hi, rain, mm) in enumerate(
            [
                (2, 24, 31, 60, 2),
                (0, 24, 32, 10, 0),
                (61, 23, 27, 90, 8),
                (3, 24, 28, 35, 0.4),
            ]
        ):
            label, style, icon = condition(code)
            days.append(
                dict(
                    date=today + timedelta(days=i),
                    low=lo,
                    high=hi,
                    rain=rain,
                    mm=mm,
                    label=label,
                    style=style,
                    icon=icon,
                )
            )
        return {"state": "ready", "days": days, "demo": True}
    key = f"care-weather:{garden.latitude}:{garden.longitude}:{garden.timezone_name}:{today}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    fields = [
        "weather_code",
        "temperature_2m_min",
        "temperature_2m_max",
        "precipitation_probability_max",
        "precipitation_sum",
    ]
    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": garden.latitude,
                "longitude": garden.longitude,
                "daily": ",".join(fields),
                "timezone": garden.timezone_name,
                "forecast_days": 4,
                "temperature_unit": "celsius",
                "precipitation_unit": "mm",
            },
            timeout=(3, 8),
        )
        response.raise_for_status()
        daily = response.json()["daily"]
        from datetime import date

        days = []
        for i, day in enumerate(daily["time"]):
            code, low, high, rain, mm = [daily[field][i] for field in fields]
            label, style, icon = condition(code)
            days.append(
                dict(
                    date=date.fromisoformat(day),
                    low=low,
                    high=high,
                    rain=rain,
                    mm=mm,
                    label=label,
                    style=style,
                    icon=icon,
                )
            )
        if not days:
            raise ValueError("Empty forecast")
    except (
        requests.RequestException,
        ValueError,
        KeyError,
        TypeError,
        IndexError,
    ) as exc:
        raise ForecastUnavailable("Forecast temporarily unavailable") from exc
    data = {"state": "ready", "days": days, "demo": False}
    cache.set(key, data, 900)
    return data
