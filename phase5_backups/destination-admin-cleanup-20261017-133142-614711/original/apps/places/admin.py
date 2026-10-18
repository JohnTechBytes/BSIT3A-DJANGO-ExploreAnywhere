# ExploreAnywhere Phase 4E.3 - Kabankalan City Destination Manager.
# Existing Place data, models, migrations and visitor routes are not modified.
from django.contrib import admin, messages
from django.utils.html import format_html, format_html_join

from apps.cities.models import City
from .forms import KabankalanPlaceAdminForm
from .models import OpeningHours, Place, PlacePhoto

KABANKALAN_CITY_ID = 2


def _photo_url(obj):
    if obj.cover_image:
        try:
            return obj.cover_image.url
        except ValueError:
            return ""
    return obj.cover_image_url or ""


def _content_gaps(obj):
    issues = []
    if not (obj.description or "").strip():
        issues.append("Description")
    if not _photo_url(obj):
        issues.append("Genuine cover photo")
    elif not (obj.photo_credit or "").strip() or not (obj.photo_license or "").strip():
        issues.append("Photo attribution/license")
    if obj.latitude is None or obj.longitude is None:
        issues.append("Verified coordinates")
    if not obj.hobbies.exists():
        issues.append("Hobby associations")
    return issues


class PlacePhotoInline(admin.StackedInline):
    model = PlacePhoto
    extra = 0
    fields = ("image", "image_url", "caption", "order", "photo_preview")
    readonly_fields = ("photo_preview",)
    verbose_name_plural = (
        "Destination gallery photos (include source, credit and license "
        "in caption: this gallery model has no dedicated rights fields)"
    )

    @admin.display(description="Gallery preview")
    def photo_preview(self, obj):
        if not obj.pk:
            return "A preview appears after saving the photo."
        try:
            url = obj.image.url if obj.image else obj.image_url
        except ValueError:
            url = ""
        if not url:
            return "No photo supplied."
        return format_html(
            '<img src="{}" alt="Gallery photo preview" '
            'style="max-width:240px;max-height:130px;object-fit:cover;border-radius:8px;">',
            url,
        )


class OpeningHoursInline(admin.TabularInline):
    model = OpeningHours
    extra = 0
    fields = ("weekday", "open_time", "close_time", "is_closed")


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    form = KabankalanPlaceAdminForm
    inlines = (PlacePhotoInline, OpeningHoursInline)
    filter_horizontal = ("hobbies",)

    list_display = (
        "title", "category", "publication", "content_status",
        "has_image", "has_map_pin", "hobby_labels", "review_count",
    )
    list_filter = ("is_verified", "is_active", "category")
    search_fields = (
        "title", "slug", "description", "address", "barangay",
        "category__name", "hobbies__name",
    )
    list_select_related = ("city", "category")
    list_per_page = 25
    readonly_fields = (
        "cover_preview", "content_checklist", "avg_rating",
        "review_count", "created_at", "updated_at",
    )
    fieldsets = (
        ("Kabankalan Destination Information", {
            "fields": ("title", "slug", "city", "category", "hobbies", "description"),
            "description": "Use verified destination details. Match hobbies to actual activities.",
        }),
        ("Address & Verified Map Location", {
            "fields": (
                "address", "barangay", "latitude", "longitude", "coordinates_confirmed",
            ),
            "description": "Missing coordinates are allowed. Verify new coordinates from a reliable source before saving.",
        }),
        ("Genuine Cover Photo & Rights", {
            "fields": (
                "cover_image", "cover_image_url", "cover_preview", "photo_credit",
                "photo_source_url", "photo_license", "photo_license_url",
            ),
            "description": "Use actual destination photography with permission. Never label sample or unrelated images as the destination.",
        }),
        ("Content Completeness", {
            "fields": ("content_checklist",),
            "description": "Warnings do not invent missing records or stop edits to legacy entries.",
        }),
        ("Contact Information", {
            "fields": ("phone", "website", "email"),
            "classes": ("collapse",),
        }),
        ("Publication Controls", {
            "fields": ("is_verified", "is_active"),
        }),
        ("Administrative Details", {
            "fields": (
                "owner", "avg_rating", "review_count", "created_at", "updated_at",
            ),
            "classes": ("collapse",),
        }),
    )
    actions = ("approve_selected", "unpublish_selected")

    def get_queryset(self, request):
        # Older nationwide rows remain in the database, but are not managed
        # from the Kabankalan-only Place admin.
        return (
            super().get_queryset(request)
            .filter(city_id=KABANKALAN_CITY_ID)
            .prefetch_related("hobbies")
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "city":
            kwargs["queryset"] = City.objects.filter(pk=KABANKALAN_CITY_ID)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        initial["city"] = KABANKALAN_CITY_ID
        return initial

    def get_readonly_fields(self, request, obj=None):
        fields = tuple(super().get_readonly_fields(request, obj))
        return fields + (("city",) if obj is not None else ())

    def save_model(self, request, obj, form, change):
        obj.city_id = KABANKALAN_CITY_ID
        super().save_model(request, obj, form, change)

    def has_view_permission(self, request, obj=None):
        if obj is not None and obj.city_id != KABANKALAN_CITY_ID:
            return False
        return super().has_view_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.city_id != KABANKALAN_CITY_ID:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.city_id != KABANKALAN_CITY_ID:
            return False
        return super().has_delete_permission(request, obj)

    @admin.display(description="Publication")
    def publication(self, obj):
        if obj.is_active and obj.is_verified:
            return format_html('<span style="color:#11753d;font-weight:700">Published</span>')
        if obj.is_active:
            return "Active · Not verified"
        return "Not published"

    @admin.display(description="Content completeness")
    def content_status(self, obj):
        gaps = _content_gaps(obj)
        if not gaps:
            return format_html('<span style="color:#11753d;font-weight:700">Ready</span>')
        return format_html(
            '<span title="{}" style="color:#9b5500;font-weight:600">{} missing</span>',
            ", ".join(gaps), len(gaps),
        )

    @admin.display(boolean=True, description="Photo")
    def has_image(self, obj):
        return bool(_photo_url(obj))

    @admin.display(boolean=True, description="Map pin")
    def has_map_pin(self, obj):
        return obj.latitude is not None and obj.longitude is not None

    @admin.display(description="Hobbies")
    def hobby_labels(self, obj):
        values = [h.name for h in obj.hobbies.all()]
        return ", ".join(values) if values else "Not assigned"

    @admin.display(description="Cover image preview")
    def cover_preview(self, obj):
        if not obj or not obj.pk:
            return "Upload a genuine image or enter a verified cover image URL."
        url = _photo_url(obj)
        if not url:
            return "No genuine cover photo has been recorded."
        return format_html(
            '<img src="{}" alt="Destination cover preview" '
            'style="width:300px;max-width:100%;max-height:180px;object-fit:cover;border-radius:10px;">',
            url,
        )

    @admin.display(description="Missing information")
    def content_checklist(self, obj):
        if not obj or not obj.pk:
            return "Save the destination to check photo, description, map, and hobby coverage."
        issues = _content_gaps(obj)
        if not issues:
            return format_html('<strong style="color:#11753d">All content checks passed.</strong>')
        items = format_html_join("", "<li>{}</li>", ((item,) for item in issues))
        return format_html(
            '<div style="color:#9b5500"><strong>Still needed:</strong><ul>{}</ul></div>',
            items,
        )

    @admin.action(description="Approve and publish selected Kabankalan destinations")
    def approve_selected(self, request, queryset):
        count = queryset.filter(city_id=KABANKALAN_CITY_ID).update(
            is_verified=True, is_active=True,
        )
        self.message_user(
            request, f"{count} Kabankalan destinations approved and published. "
            "Check content-completeness warnings before sharing a destination.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Unpublish selected Kabankalan destinations")
    def unpublish_selected(self, request, queryset):
        count = queryset.filter(city_id=KABANKALAN_CITY_ID).update(is_active=False)
        self.message_user(
            request, f"{count} Kabankalan destinations unpublished.",
            level=messages.SUCCESS,
        )
