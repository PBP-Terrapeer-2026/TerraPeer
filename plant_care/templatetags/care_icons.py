from pathlib import Path
from functools import lru_cache
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
@lru_cache(maxsize=30)
def icon(name):
    # Only repository-owned SVGs, never an arbitrary filename from user input.
    allowed = {
        "plus",
        "close",
        "arrow",
        "check",
        "edit",
        "trash",
        "repeat",
        "water",
        "leaf",
        "sprout",
        "sun",
        "rain",
        "cloud",
        "cloudsun",
        "location",
        "calendar",
        "inspect",
        "prune",
    }
    if name not in allowed:
        return ""
    svg = (
        Path(settings.BASE_DIR) / "static" / "terrapeer" / "icons" / (name + ".svg")
    ).read_text(encoding="utf-8")
    return mark_safe('<span class="icon" aria-hidden="true">' + svg + "</span>")
