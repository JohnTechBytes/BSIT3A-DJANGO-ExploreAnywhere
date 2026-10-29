from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        USER = "user", "User"
        SUPER_ADMIN = "super_admin", "Super Admin"
        CITY_ADMIN = "city_admin", "City Admin"
        BUSINESS_OWNER = "business_owner", "Business Owner"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
        db_index=True,
    )
    managed_city = models.ForeignKey(
        "cities.City",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="city_admins",
        help_text="City managed by this admin (if role is city_admin).",
    )
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    consent_privacy = models.BooleanField(
        default=False,
        help_text="The visitor accepted the privacy notice when the account was created.",
    )
    consent_privacy_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the privacy notice was accepted.",
    )

    class Meta:
        db_table = "accounts_user"

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN or self.is_superuser

    @property
    def is_city_admin(self):
        return self.role == self.Role.CITY_ADMIN

    @property
    def is_business_owner(self):
        return self.role == self.Role.BUSINESS_OWNER
