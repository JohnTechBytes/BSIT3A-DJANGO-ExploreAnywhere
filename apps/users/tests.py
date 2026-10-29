"""Tests for the accounts app: URL hygiene, the legacy alias and staff admin."""
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.cities.models import City

User = get_user_model()


class AccountUrlTests(TestCase):
    """The branded account routes must own the canonical URL names."""

    def setUp(self):
        # The city-locking middleware requires the Kabankalan city row (id 2).
        City.objects.get_or_create(id=2, defaults={"name": "Kabankalan"})

    def test_login_name_resolves_to_the_branded_accounts_route(self):
        self.assertEqual(reverse("login"), "/accounts/login/")

    def test_register_and_logout_names_resolve_to_the_accounts_routes(self):
        self.assertEqual(reverse("register"), "/accounts/register/")
        self.assertEqual(reverse("logout"), "/accounts/logout/")

    def test_legacy_users_login_route_still_serves_the_branded_page(self):
        response = self.client.get("/users/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "auth-card")

    def test_legacy_users_login_route_still_signs_a_user_in(self):
        User.objects.create_user(username="legacy_user", password="legacy-pass-2026")
        response = self.client.post(
            "/users/login/", {"username": "legacy_user", "password": "legacy-pass-2026"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)


class UserAdminTests(TestCase):
    """The custom user model has to be reachable from the staff dashboard."""

    def setUp(self):
        # The city-locking middleware requires the Kabankalan city row (id 2).
        City.objects.get_or_create(id=2, defaults={"name": "Kabankalan"})
        self.admin_user = User.objects.create_superuser(
            username="staff_admin", email="staff@example.com", password="staff-pass-2026"
        )
        self.client.force_login(self.admin_user)

    def test_custom_user_model_is_registered_in_the_admin(self):
        self.assertIn(User, admin.site._registry)
        self.assertEqual(admin.site._registry[User].__class__.__name__, "ExploreUserAdmin")

    def test_admin_index_shows_the_manage_users_shortcut(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manage users")
        self.assertContains(response, "/admin/users/user/")

    def test_user_changelist_and_add_form_render(self):
        response = self.client.get("/admin/users/user/")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/admin/users/user/add/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kabankalan role")

    def test_admin_can_create_an_account_with_a_role(self):
        response = self.client.post(
            "/admin/users/user/add/",
            {
                "username": "created_by_staff",
                "email": "created@example.com",
                "password1": "created-pass-2026",
                "password2": "created-pass-2026",
                "role": "city_admin",
                "managed_city": "",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        created = User.objects.get(username="created_by_staff")
        self.assertEqual(created.role, User.Role.CITY_ADMIN)
