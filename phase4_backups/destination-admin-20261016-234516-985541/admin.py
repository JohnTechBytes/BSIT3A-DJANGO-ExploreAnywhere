
from django.contrib import admin, messages
from django.db.models import Count

from .models import Place


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "city_name",
        "province_name",
        "category",
        "is_verified",
        "is_active",
        "has_image",
    )

    list_filter = (
        "is_verified",
        "is_active",
        "category",
    )

    search_fields = (
        "title",
        "slug",
        "city__name",
        "city__province",
        "address",
    )

    list_select_related = (
        "city",
        "category",
    )

    list_per_page = 50

    readonly_fields = (
        "avg_rating",
        "review_count",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Attraction Information",
            {
                "fields": (
                    "title",
                    "slug",
                    "city",
                    "category",
                    "description",
                )
            },
        ),
        (
            "Location",
            {
                "fields": (
                    "address",
                    "barangay",
                    "latitude",
                    "longitude",
                )
            },
        ),
        (
            "Images",
            {
                "fields": (
                    "cover_image",
                    "cover_image_url",
                )
            },
        ),
        (
            "Contact Information",
            {
                "fields": (
                    "phone",
                    "website",
                    "email",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Review and Publication",
            {
                "fields": (
                    "is_verified",
                    "is_active",
                )
            },
        ),
        (
            "Additional Information",
            {
                "fields": (
                    "owner",
                    "avg_rating",
                    "review_count",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    actions = (
        "approve_selected",
        "unpublish_selected",
    )

    @admin.display(description="City", ordering="city__name")
    def city_name(self, obj):
        return obj.city.name

    @admin.display(description="Province", ordering="city__province")
    def province_name(self, obj):
        return obj.city.province

    @admin.display(boolean=True, description="Image")
    def has_image(self, obj):
        return bool(obj.cover_image or obj.cover_image_url)

    @admin.action(description="Approve and publish selected attractions")
    def approve_selected(self, request, queryset):
        count = queryset.update(
            is_verified=True,
            is_active=True,
        )
        self.message_user(
            request,
            f"{count} attractions approved and published.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Unpublish selected attractions")
    def unpublish_selected(self, request, queryset):
        count = queryset.update(
            is_active=False,
        )
        self.message_user(
            request,
            f"{count} attractions unpublished.",
            level=messages.SUCCESS,
        )
