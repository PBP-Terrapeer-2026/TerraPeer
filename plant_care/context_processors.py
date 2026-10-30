from django.conf import settings
from django.urls import NoReverseMatch, reverse

NAV_ITEMS = (
    ("Home", "home"),
    ("Garden Setup", "setup"),
    ("Planning", "planning"),
    ("My Plants", "plants"),
    ("Plant Care", "care"),
    ("Journal", "journal"),
)


def care_navigation(request):
    routes = {
        "home": "show_main",
        "setup": "garden_setup:space_list",
        "planning": "garden_planning:index",
        "care": "care:choose",
        "plants": "my_plants:list",
        "journal": "garden_journal",
    }
    routes.update(getattr(settings, "CARE_NAV_ROUTES", {}))
    items = []
    for label, key in NAV_ITEMS:
        try:
            url = reverse(routes[key])
        except (KeyError, NoReverseMatch):
            url = None
        items.append({"label": label, "key": key, "url": url, "active": key == "care"})
    match = getattr(request, "resolver_match", None)
    care_layout = bool(match and match.app_name == "care")
    has_legacy_tasks = False
    if care_layout and request.user.is_authenticated:
        from .models import CareTask

        has_legacy_tasks = CareTask.objects.filter(
            plant__isnull=True,
            legacy_plant__garden__owner=request.user,
        ).exists()
    return {
        "has_legacy_tasks": has_legacy_tasks,
        "care_nav_items": items,
        "care_demo": getattr(settings, "CARE_DEMO", False),
        "care_layout": care_layout,
    }
