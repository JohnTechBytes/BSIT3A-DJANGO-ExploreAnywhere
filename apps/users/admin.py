"""Staff administration for the ExploreAnywhere accounts.

``AUTH_USER_MODEL`` points at ``users.User``, so ``django.contrib.auth.admin.UserAdmin``
is bound to the wrong model by default (``auth.User``) and cannot be used as-is.
``ExploreUserAdmin`` below re-binds the admin forms to the real user model and
adds the Kabankalan-specific role fields.
"""
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .auth_forms import ExploreUserChangeForm, ExploreUserCreationForm

User = get_user_model()


@admin.register(User)
class ExploreUserAdmin(UserAdmin):
    form = ExploreUserChangeForm
    add_form = ExploreUserCreationForm

    list_display = (
        "username",
        "email",
        "role",
        "managed_city",
        "is_active",
        "is_staff",
    )
    list_filter = ("role", "managed_city", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "first_name", "last_name", "email")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email", "bio")}),
        (
            "Kabankalan role",
            {
                "fields": ("role", "managed_city", "avatar", "latitude", "longitude"),
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2"),
            },
        ),
        (
            "Kabankalan role",
            {"classes": ("wide",), "fields": ("role", "managed_city")},
        ),
    )
