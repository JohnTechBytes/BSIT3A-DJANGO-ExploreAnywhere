"""Public, read-only City Information module.

The records shown here are published by staff in the administrative panel
(Admin > City information). This page only displays what the city
administration actually published for Kabankalan; it never invents content and
it never offers editing controls to visitors.
"""
from django.db.models import Count, Q
from django.shortcuts import render

from apps.cities.locking import LOCKED_CITY_PK, locked_city

from .models import CityInformation


def city_information(request):
    """List the published City Information entries for Kabankalan."""
    city = locked_city() or City.objects.filter(pk=LOCKED_CITY_PK).first()
    if city is None:
        entries = CityInformation.objects.none()
    else:
        entries = CityInformation.objects.filter(city=city)

    # Type filter (one of the published categories).
    selected_type = (request.GET.get("type") or "").strip()
    valid_types = {value for value, _ in CityInformation.InfoType.choices}
    if selected_type not in valid_types:
        selected_type = ""

    # Free text filter over the published title and description.
    search_query = (request.GET.get("q") or "").strip()[:100]
    if search_query:
        entries = entries.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )
    if selected_type:
        entries = entries.filter(info_type=selected_type)

    published = list(entries.order_by("info_type", "order", "pk"))

    grouped = []
    for info_type, label in CityInformation.InfoType.choices:
        items = [entry for entry in published if entry.info_type == info_type]
        if items:
            grouped.append({"type": info_type, "label": label, "items": items})

    # The type chips always show the total number of published entries, even
    # while a search or another type is active.
    if city is None:
        type_counts = {}
    else:
        type_counts = {
            row["info_type"]: row["total"]
            for row in CityInformation.objects.filter(city=city)
            .values("info_type")
            .annotate(total=Count("id"))
        }
    type_links = [
        {
            "type": info_type,
            "label": label,
            "count": type_counts.get(info_type, 0),
            "active": info_type == selected_type,
        }
        for info_type, label in CityInformation.InfoType.choices
    ]

    return render(
        request,
        "info/city_information.html",
        {
            "selected_city": city,
            "grouped_entries": grouped,
            "entry_count": len(published),
            "total_count": sum(type_counts.values()),
            "type_links": type_links,
            "selected_type": selected_type,
            "search_query": search_query,
        },
    )
