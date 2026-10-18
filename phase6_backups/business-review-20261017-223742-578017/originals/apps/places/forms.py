# ExploreAnywhere Phase 4E.3 - Kabankalan destination editing checks.
# This admin-only form does not change database models or migrations.
from django import forms
from .models import Place


class KabankalanPlaceAdminForm(forms.ModelForm):
    coordinates_confirmed = forms.BooleanField(
        required=False,
        label="I checked these coordinates against a reliable map/source",
        help_text=(
            "Required only when changing the latitude or longitude. "
            "Do not guess a location to make the map marker appear."
        ),
    )

    class Meta:
        model = Place
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()

        # A city-locked admin must not accept posted city IDs for other places.
        city = cleaned.get("city")
        if city is not None and city.pk != 2:
            self.add_error("city", "This manager only publishes Kabankalan City destinations.")
        if self.instance.pk and self.instance.city_id != 2:
            raise forms.ValidationError("This destination does not belong to Kabankalan City.")

        latitude = cleaned.get("latitude")
        longitude = cleaned.get("longitude")
        if (latitude is None) != (longitude is None):
            message = "Enter both latitude and longitude, or leave both blank."
            self.add_error("latitude" if latitude is None else "longitude", message)
        else:
            if latitude is not None and not (-90 <= latitude <= 90):
                self.add_error("latitude", "Latitude must be between -90 and 90.")
            if longitude is not None and not (-180 <= longitude <= 180):
                self.add_error("longitude", "Longitude must be between -180 and 180.")
            if (
                latitude is not None
                and longitude is not None
                and ("latitude" in self.changed_data or "longitude" in self.changed_data)
                and not cleaned.get("coordinates_confirmed")
            ):
                self.add_error(
                    "coordinates_confirmed",
                    "Confirm that you independently checked the location before saving new coordinates.",
                )

        has_photo = bool(cleaned.get("cover_image") or cleaned.get("cover_image_url"))
        changed_photo = "cover_image" in self.changed_data or "cover_image_url" in self.changed_data
        # Legacy images can still have missing credits: don't block unrelated
        # edits, but ensure newly changed cover photos carry basic attribution.
        if has_photo and changed_photo:
            if not (cleaned.get("photo_credit") or "").strip():
                self.add_error("photo_credit", "Add the photographer/owner attribution for this cover photo.")
            if not (cleaned.get("photo_license") or "").strip():
                self.add_error("photo_license", "Record the photo permission or license for this cover photo.")
            if cleaned.get("cover_image_url") and not (cleaned.get("photo_source_url") or "").strip():
                self.add_error("photo_source_url", "External cover photos need a traceable source URL.")

        return cleaned
