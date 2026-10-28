from django.db import models
from django.conf import settings


class Itinerary(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="itineraries",
    )
    city = models.ForeignKey(
        "cities.City",
        on_delete=models.CASCADE,
        related_name="itineraries",
    )
    title = models.CharField(max_length=255, default="My Itinerary")
    day_number = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "explore_itineraries"
        verbose_name_plural = "Itineraries"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - Day {self.day_number} ({self.city.name})"


class ItineraryStop(models.Model):
    itinerary = models.ForeignKey(
        Itinerary,
        on_delete=models.CASCADE,
        related_name="stops",
    )
    place = models.ForeignKey(
        "places.Place",
        on_delete=models.CASCADE,
        related_name="itinerary_stops",
    )
    start_time = models.TimeField()
    stop_order = models.PositiveIntegerField(default=1)
    notes = models.CharField(max_length=255, blank=True)
    distance_from_prev_km = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00, blank=True, null=True
    )

    class Meta:
        db_table = "explore_itinerary_stops"
        ordering = ["stop_order", "start_time"]

    def __str__(self):
        return f"Stop {self.stop_order}: {self.place.title} @ {self.start_time}"
