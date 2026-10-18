"""Staff-reviewed check-in records; a self-report is not proof of presence."""
from django.conf import settings
from django.db import models


class VisitCheckIn(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending staff review"
        APPROVED = "approved", "Staff approved"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="kabankalan_checkins",
    )
    place = models.ForeignKey(
        "places.Place", on_delete=models.CASCADE,
        related_name="visitor_checkins",
    )
    visited_on = models.DateField()
    visit_note = models.TextField(max_length=1000)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING,
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="moderated_kabankalan_checkins",
    )
    reviewer_note = models.TextField(blank=True)

    class Meta:
        db_table = "explore_visit_checkins"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "place"], name="unique_visit_user_place",
            ),
        ]
        ordering = ["-submitted_at", "-pk"]

    def __str__(self):
        return f"{self.user} / {self.place} / {self.status}"
