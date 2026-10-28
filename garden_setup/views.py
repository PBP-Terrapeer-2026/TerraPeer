from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from .models import GrowingSpace

@login_required(login_url="login")
def space_list(request):
    owned_spaces = GrowingSpace.objects.filter(
        user=request.user
    )

    total_count = owned_spaces.count()
    indoor_count = owned_spaces.filter(
        environment=GrowingSpace.Environment.INDOOR
    ).count()
    outdoor_count = owned_spaces.filter(
        environment=GrowingSpace.Environment.OUTDOOR
    ).count()
    search_query = request.GET.get(
        "q", ""
    ).strip()[:100]
    selected_environment = request.GET.get(
        "environment", ""
    )

    if selected_environment not in ("indoor", "outdoor"):
        selected_environment = ""

    spaces = owned_spaces

    if search_query:
        spaces = spaces.filter(
            Q(name__icontains=search_query) |
            Q(city__icontains=search_query)
        )

    if selected_environment:
        spaces = spaces.filter(
            environment=selected_environment
        )

    return render(
        request,
        "garden_setup/space_list.html",
        {
            "spaces": spaces,
            "search_query": search_query,
            "selected_environment": selected_environment,
            "total_count": total_count,
            "indoor_count": indoor_count,
            "outdoor_count": outdoor_count,
            "has_filters": bool(
                search_query or selected_environment
            ),
        },
    )
