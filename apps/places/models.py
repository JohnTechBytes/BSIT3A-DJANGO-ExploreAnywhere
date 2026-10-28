from django.db import models
from django.conf import settings
from datetime import datetime
from django.utils import timezone


class Place(models.Model):
    city = models.ForeignKey(
        "cities.City",
        on_delete=models.CASCADE,
        related_name="places",
        db_index=True,
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    category = models.ForeignKey(
        "core.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="places",
    )
    hobbies = models.ManyToManyField(
        "core.Hobby",
        blank=True,
        related_name="places",
    )

    description = models.TextField(blank=True)
    address = models.CharField(max_length=255)
    barangay = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_places",
    )
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    review_count = models.PositiveIntegerField(default=0)
    cover_image = models.ImageField(upload_to="places/covers/", blank=True, null=True)
    cover_image_url = models.URLField(
    max_length=2048,
    blank=True,
)
    
    photo_credit = models.CharField(
        max_length=500, blank=True
    )
    photo_source_url = models.URLField(
        blank=True, max_length=1000
    )
    photo_license = models.CharField(
        max_length=100, blank=True
    )
    photo_license_url = models.URLField(
        blank=True, max_length=1000
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "explore_places"
        ordering = ["-avg_rating", "title"]

    def __str__(self):
        return f"{self.title} ({self.city.name})"

    @property
    def photo_url(self):
        if self.cover_image:
            return self.cover_image.url
        if self.cover_image_url:
            return self.cover_image_url
        return "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=600&auto=format&fit=crop"

    def is_open_now(self):
        now = timezone.localtime(timezone.now())
        current_weekday = now.weekday()  # 0=Monday, 6=Sunday
        current_time = now.time()
        hours = self.opening_hours.filter(weekday=current_weekday).first()
        if not hours:
            return None  # No hours specified
        if hours.is_closed:
            return False
        if hours.open_time and hours.close_time:
            if hours.open_time <= hours.close_time:
                return hours.open_time <= current_time <= hours.close_time
            else:  # Spans midnight
                return current_time >= hours.open_time or current_time <= hours.close_time
        return True


class OpeningHours(models.Model):
    WEEKDAYS = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]
    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="opening_hours",
    )
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAYS)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        db_table = "explore_opening_hours"
        unique_together = ("place", "weekday")
        ordering = ["weekday"]

    def __str__(self):
        if self.is_closed:
            return f"{self.place.title} - {self.get_weekday_display()}: Closed"
        return f"{self.place.title} - {self.get_weekday_display()}: {self.open_time} - {self.close_time}"


class PlacePhoto(models.Model):
    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image = models.ImageField(upload_to="places/photos/", blank=True, null=True)
    image_url = models.URLField(blank=True)
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "explore_place_photos"
        ordering = ["order"]

    @property
    def display_url(self):
        if self.image:
            return self.image.url
        return self.image_url or "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=600&auto=format&fit=crop"


class Review(models.Model):
    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="place_reviews",
    )
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "explore_reviews"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} on {self.place.title} ({self.rating}★)"


class SavedPlace(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_places",
    )
    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="saved_by_users",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "explore_saved_places"
        unique_together = ("user", "place")
