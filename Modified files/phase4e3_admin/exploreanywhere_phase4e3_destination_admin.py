#!/usr/bin/env python3
"""Install Phase 4E.3 Kabankalan Destination Admin using vetted existing source.

Usage: python exploreanywhere_phase4e3_destination_admin.py [--dry-run]
Only apps/places/admin.py and apps/places/forms.py are written.
"""
import argparse
import hashlib
import shutil
import sys
from datetime import datetime
from pathlib import Path

EXPECTED_ADMIN_SHA256 = "35257938e05ce81169b737095adc59fc7495fe20625d47ad75fdd7df2d43abd4"
MARKER = "ExploreAnywhere Phase 4E.3"
FORM_CONTENT = '# ExploreAnywhere Phase 4E.3 - Kabankalan destination editing checks.\n# This admin-only form does not change database models or migrations.\nfrom django import forms\nfrom .models import Place\n\n\nclass KabankalanPlaceAdminForm(forms.ModelForm):\n    coordinates_confirmed = forms.BooleanField(\n        required=False,\n        label="I checked these coordinates against a reliable map/source",\n        help_text=(\n            "Required only when changing the latitude or longitude. "\n            "Do not guess a location to make the map marker appear."\n        ),\n    )\n\n    class Meta:\n        model = Place\n        fields = "__all__"\n\n    def clean(self):\n        cleaned = super().clean()\n\n        # A city-locked admin must not accept posted city IDs for other places.\n        city = cleaned.get("city")\n        if city is not None and city.pk != 2:\n            self.add_error("city", "This manager only publishes Kabankalan City destinations.")\n        if self.instance.pk and self.instance.city_id != 2:\n            raise forms.ValidationError("This destination does not belong to Kabankalan City.")\n\n        latitude = cleaned.get("latitude")\n        longitude = cleaned.get("longitude")\n        if (latitude is None) != (longitude is None):\n            message = "Enter both latitude and longitude, or leave both blank."\n            self.add_error("latitude" if latitude is None else "longitude", message)\n        else:\n            if latitude is not None and not (-90 <= latitude <= 90):\n                self.add_error("latitude", "Latitude must be between -90 and 90.")\n            if longitude is not None and not (-180 <= longitude <= 180):\n                self.add_error("longitude", "Longitude must be between -180 and 180.")\n            if (\n                latitude is not None\n                and longitude is not None\n                and ("latitude" in self.changed_data or "longitude" in self.changed_data)\n                and not cleaned.get("coordinates_confirmed")\n            ):\n                self.add_error(\n                    "coordinates_confirmed",\n                    "Confirm that you independently checked the location before saving new coordinates.",\n                )\n\n        has_photo = bool(cleaned.get("cover_image") or cleaned.get("cover_image_url"))\n        changed_photo = "cover_image" in self.changed_data or "cover_image_url" in self.changed_data\n        # Legacy images can still have missing credits: don\'t block unrelated\n        # edits, but ensure newly changed cover photos carry basic attribution.\n        if has_photo and changed_photo:\n            if not (cleaned.get("photo_credit") or "").strip():\n                self.add_error("photo_credit", "Add the photographer/owner attribution for this cover photo.")\n            if not (cleaned.get("photo_license") or "").strip():\n                self.add_error("photo_license", "Record the photo permission or license for this cover photo.")\n            if cleaned.get("cover_image_url") and not (cleaned.get("photo_source_url") or "").strip():\n                self.add_error("photo_source_url", "External cover photos need a traceable source URL.")\n\n        return cleaned\n'
ADMIN_CONTENT = '# ExploreAnywhere Phase 4E.3 - Kabankalan City Destination Manager.\n# Existing Place data, models, migrations and visitor routes are not modified.\nfrom django.contrib import admin, messages\nfrom django.utils.html import format_html, format_html_join\n\nfrom apps.cities.models import City\nfrom .forms import KabankalanPlaceAdminForm\nfrom .models import OpeningHours, Place, PlacePhoto\n\nKABANKALAN_CITY_ID = 2\n\n\ndef _photo_url(obj):\n    if obj.cover_image:\n        try:\n            return obj.cover_image.url\n        except ValueError:\n            return ""\n    return obj.cover_image_url or ""\n\n\ndef _content_gaps(obj):\n    issues = []\n    if not (obj.description or "").strip():\n        issues.append("Description")\n    if not _photo_url(obj):\n        issues.append("Genuine cover photo")\n    elif not (obj.photo_credit or "").strip() or not (obj.photo_license or "").strip():\n        issues.append("Photo attribution/license")\n    if obj.latitude is None or obj.longitude is None:\n        issues.append("Verified coordinates")\n    if not obj.hobbies.exists():\n        issues.append("Hobby associations")\n    return issues\n\n\nclass PlacePhotoInline(admin.StackedInline):\n    model = PlacePhoto\n    extra = 0\n    fields = ("image", "image_url", "caption", "order", "photo_preview")\n    readonly_fields = ("photo_preview",)\n    verbose_name_plural = (\n        "Destination gallery photos (include source, credit and license "\n        "in caption: this gallery model has no dedicated rights fields)"\n    )\n\n    @admin.display(description="Gallery preview")\n    def photo_preview(self, obj):\n        if not obj.pk:\n            return "A preview appears after saving the photo."\n        try:\n            url = obj.image.url if obj.image else obj.image_url\n        except ValueError:\n            url = ""\n        if not url:\n            return "No photo supplied."\n        return format_html(\n            \'<img src="{}" alt="Gallery photo preview" \'\n            \'style="max-width:240px;max-height:130px;object-fit:cover;border-radius:8px;">\',\n            url,\n        )\n\n\nclass OpeningHoursInline(admin.TabularInline):\n    model = OpeningHours\n    extra = 0\n    fields = ("weekday", "open_time", "close_time", "is_closed")\n\n\n@admin.register(Place)\nclass PlaceAdmin(admin.ModelAdmin):\n    form = KabankalanPlaceAdminForm\n    inlines = (PlacePhotoInline, OpeningHoursInline)\n    filter_horizontal = ("hobbies",)\n\n    list_display = (\n        "title", "category", "publication", "content_status",\n        "has_image", "has_map_pin", "hobby_labels", "review_count",\n    )\n    list_filter = ("is_verified", "is_active", "category")\n    search_fields = (\n        "title", "slug", "description", "address", "barangay",\n        "category__name", "hobbies__name",\n    )\n    list_select_related = ("city", "category")\n    list_per_page = 25\n    readonly_fields = (\n        "cover_preview", "content_checklist", "avg_rating",\n        "review_count", "created_at", "updated_at",\n    )\n    fieldsets = (\n        ("Kabankalan Destination Information", {\n            "fields": ("title", "slug", "city", "category", "hobbies", "description"),\n            "description": "Use verified destination details. Match hobbies to actual activities.",\n        }),\n        ("Address & Verified Map Location", {\n            "fields": (\n                "address", "barangay", "latitude", "longitude", "coordinates_confirmed",\n            ),\n            "description": "Missing coordinates are allowed. Verify new coordinates from a reliable source before saving.",\n        }),\n        ("Genuine Cover Photo & Rights", {\n            "fields": (\n                "cover_image", "cover_image_url", "cover_preview", "photo_credit",\n                "photo_source_url", "photo_license", "photo_license_url",\n            ),\n            "description": "Use actual destination photography with permission. Never label sample or unrelated images as the destination.",\n        }),\n        ("Content Completeness", {\n            "fields": ("content_checklist",),\n            "description": "Warnings do not invent missing records or stop edits to legacy entries.",\n        }),\n        ("Contact Information", {\n            "fields": ("phone", "website", "email"),\n            "classes": ("collapse",),\n        }),\n        ("Publication Controls", {\n            "fields": ("is_verified", "is_active"),\n        }),\n        ("Administrative Details", {\n            "fields": (\n                "owner", "avg_rating", "review_count", "created_at", "updated_at",\n            ),\n            "classes": ("collapse",),\n        }),\n    )\n    actions = ("approve_selected", "unpublish_selected")\n\n    def get_queryset(self, request):\n        # Older nationwide rows remain in the database, but are not managed\n        # from the Kabankalan-only Place admin.\n        return (\n            super().get_queryset(request)\n            .filter(city_id=KABANKALAN_CITY_ID)\n            .prefetch_related("hobbies")\n        )\n\n    def formfield_for_foreignkey(self, db_field, request, **kwargs):\n        if db_field.name == "city":\n            kwargs["queryset"] = City.objects.filter(pk=KABANKALAN_CITY_ID)\n        return super().formfield_for_foreignkey(db_field, request, **kwargs)\n\n    def get_changeform_initial_data(self, request):\n        initial = super().get_changeform_initial_data(request)\n        initial["city"] = KABANKALAN_CITY_ID\n        return initial\n\n    def get_readonly_fields(self, request, obj=None):\n        fields = tuple(super().get_readonly_fields(request, obj))\n        return fields + (("city",) if obj is not None else ())\n\n    def save_model(self, request, obj, form, change):\n        obj.city_id = KABANKALAN_CITY_ID\n        super().save_model(request, obj, form, change)\n\n    def has_view_permission(self, request, obj=None):\n        if obj is not None and obj.city_id != KABANKALAN_CITY_ID:\n            return False\n        return super().has_view_permission(request, obj)\n\n    def has_change_permission(self, request, obj=None):\n        if obj is not None and obj.city_id != KABANKALAN_CITY_ID:\n            return False\n        return super().has_change_permission(request, obj)\n\n    def has_delete_permission(self, request, obj=None):\n        if obj is not None and obj.city_id != KABANKALAN_CITY_ID:\n            return False\n        return super().has_delete_permission(request, obj)\n\n    @admin.display(description="Publication")\n    def publication(self, obj):\n        if obj.is_active and obj.is_verified:\n            return format_html(\'<span style="color:#11753d;font-weight:700">Published</span>\')\n        if obj.is_active:\n            return "Active · Not verified"\n        return "Not published"\n\n    @admin.display(description="Content completeness")\n    def content_status(self, obj):\n        gaps = _content_gaps(obj)\n        if not gaps:\n            return format_html(\'<span style="color:#11753d;font-weight:700">Ready</span>\')\n        return format_html(\n            \'<span title="{}" style="color:#9b5500;font-weight:600">{} missing</span>\',\n            ", ".join(gaps), len(gaps),\n        )\n\n    @admin.display(boolean=True, description="Photo")\n    def has_image(self, obj):\n        return bool(_photo_url(obj))\n\n    @admin.display(boolean=True, description="Map pin")\n    def has_map_pin(self, obj):\n        return obj.latitude is not None and obj.longitude is not None\n\n    @admin.display(description="Hobbies")\n    def hobby_labels(self, obj):\n        values = [h.name for h in obj.hobbies.all()]\n        return ", ".join(values) if values else "Not assigned"\n\n    @admin.display(description="Cover image preview")\n    def cover_preview(self, obj):\n        if not obj or not obj.pk:\n            return "Upload a genuine image or enter a verified cover image URL."\n        url = _photo_url(obj)\n        if not url:\n            return "No genuine cover photo has been recorded."\n        return format_html(\n            \'<img src="{}" alt="Destination cover preview" \'\n            \'style="width:300px;max-width:100%;max-height:180px;object-fit:cover;border-radius:10px;">\',\n            url,\n        )\n\n    @admin.display(description="Missing information")\n    def content_checklist(self, obj):\n        if not obj or not obj.pk:\n            return "Save the destination to check photo, description, map, and hobby coverage."\n        issues = _content_gaps(obj)\n        if not issues:\n            return format_html(\'<strong style="color:#11753d">All content checks passed.</strong>\')\n        items = format_html_join("", "<li>{}</li>", ((item,) for item in issues))\n        return format_html(\n            \'<div style="color:#9b5500"><strong>Still needed:</strong><ul>{}</ul></div>\',\n            items,\n        )\n\n    @admin.action(description="Approve and publish selected Kabankalan destinations")\n    def approve_selected(self, request, queryset):\n        count = queryset.filter(city_id=KABANKALAN_CITY_ID).update(\n            is_verified=True, is_active=True,\n        )\n        self.message_user(\n            request, f"{count} Kabankalan destinations approved and published. "\n            "Check content-completeness warnings before sharing a destination.",\n            level=messages.SUCCESS,\n        )\n\n    @admin.action(description="Unpublish selected Kabankalan destinations")\n    def unpublish_selected(self, request, queryset):\n        count = queryset.filter(city_id=KABANKALAN_CITY_ID).update(is_active=False)\n        self.message_user(\n            request, f"{count} Kabankalan destinations unpublished.",\n            level=messages.SUCCESS,\n        )\n'


def sha_normalized(raw):
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def run():
    parser = argparse.ArgumentParser(description="Install Kabankalan-only admin improvements")
    parser.add_argument("--dry-run", action="store_true", help="Check safety guards without changing files")
    args = parser.parse_args()
    project = Path.cwd()
    admin_file = project / "apps" / "places" / "admin.py"
    forms_file = project / "apps" / "places" / "forms.py"
    model_file = project / "apps" / "places" / "models.py"
    city_model_file = project / "apps" / "cities" / "models.py"
    if not (project / "manage.py").is_file() or not all(
        f.is_file() for f in (admin_file, model_file, city_model_file)
    ):
        sys.exit("STOP: Run this script from the ExploreAnywhere project root (next to manage.py).")

    existing_admin = admin_file.read_bytes()
    existing_forms = forms_file.read_bytes() if forms_file.exists() else None
    if sha_normalized(existing_admin) == sha_normalized(ADMIN_CONTENT.encode("utf-8")):
        if existing_forms is not None and sha_normalized(existing_forms) == sha_normalized(FORM_CONTENT.encode("utf-8")):
            print("ALREADY INSTALLED: Destination admin UI is already in place. No changes made.")
            return
        sys.exit("STOP: Admin appears installed but forms.py differs. No changes made.")
    if sha_normalized(existing_admin) != EXPECTED_ADMIN_SHA256:
        sys.exit("STOP: admin.py has changed since the uploaded ZIP. No files modified. Send the latest admin.py to ChatGPT.")
    if existing_forms is not None and existing_forms.strip():
        sys.exit("STOP: forms.py is no longer empty. No files modified; this installer will not overwrite it.")
    model_text = model_file.read_text(encoding="utf-8-sig")
    required = (
        "class Place(", "class PlacePhoto(", "class OpeningHours(",
        "photo_credit", "photo_source_url", "photo_license",
        "photo_license_url", "hobbies", "cover_image", "cover_image_url",
    )
    if any(token not in model_text for token in required):
        sys.exit("STOP: The Place model differs from the uploaded version. No files modified.")
    try:
        compile(FORM_CONTENT, str(forms_file), "exec")
        compile(ADMIN_CONTENT, str(admin_file), "exec")
    except SyntaxError as e:
        sys.exit(f"STOP: Generated Python has a syntax error: {e}")
    if args.dry_run:
        print("DRY RUN OK: source hash and model fields match; safe to install with automatic backups.")
        print("Will change ONLY apps/places/admin.py and apps/places/forms.py; no database records or migrations.")
        return

    backup = project / "phase4_backups" / ("destination-admin-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    backup.mkdir(parents=True, exist_ok=False)
    shutil.copy2(admin_file, backup / "admin.py")
    if forms_file.exists():
        shutil.copy2(forms_file, backup / "forms.py")

    # Write forms before importing from them in the newly installed admin.
    try:
        forms_file.write_text(FORM_CONTENT, encoding="utf-8", newline="\n")
        admin_file.write_text(ADMIN_CONTENT, encoding="utf-8", newline="\n")
    except Exception:
        shutil.copy2(backup / "admin.py", admin_file)
        if (backup / "forms.py").exists():
            shutil.copy2(backup / "forms.py", forms_file)
        elif forms_file.exists():
            forms_file.unlink()
        raise
    print("SUCCESS: Phase 4E.3 Kabankalan Destination Manager installed.")
    print("Changed: apps/places/admin.py and apps/places/forms.py only.")
    print("Added: hobby selector, admin photo/gallery previews, metadata, coordinate confirmation, content warnings, city-locked admin, opening hours inline.")
    print("Backups:", backup)
    print("No migrations, database records, destination photos, API keys or visitor templates modified.")
    print("NEXT: python manage.py check")
    print("NEXT: python manage.py makemigrations --check --dry-run")
    print("NEXT: open /admin/places/place/ and inspect Amyan Hill + Kabankalan Plaza.")


if __name__ == "__main__":
    run()
