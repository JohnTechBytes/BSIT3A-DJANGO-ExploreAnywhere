
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.shortcuts import render

from .models import Place


@staff_member_required
def admin_photo_preview(request):
    photos = (
        Place.objects
        .select_related("city")
        .exclude(photo_source_url="")
        .exclude(cover_image_url="")
        .order_by("title", "id")
    )

    paginator = Paginator(photos, 24)
    page = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "places/admin_photo_preview.html",
        {
            "page_obj": page,
            "photo_count": paginator.count,
        },
    )
