from django.conf import settings
from django.urls import NoReverseMatch, reverse

NAV_ITEMS = (
    ("Home", "home"),
    ("Garden Setup", "setup"),
    ("Planning", "planning"),
    ("My Plants", "plants"),
    ("Plant Care", "care"),
    ("Journal", "journal"),
    ("Explore", "explore"),
)


def care_navigation(request):
    routes = {"home": "show_main", "care": "care:choose", "journal": "garden_journal"}
    routes.update(getattr(settings, "CARE_NAV_ROUTES", {}))
    items = []
    for label, key in NAV_ITEMS:
        try:
            url = reverse(routes[key])
        except (KeyError, NoReverseMatch):
            url = None
        items.append({"label": label, "key": key, "url": url, "active": key == "care"})
    return {"care_nav_items": items, "care_demo": getattr(settings, "CARE_DEMO", False)}
