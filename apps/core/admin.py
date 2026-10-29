"""Staff-dashboard housekeeping.

The city office works with accounts through the project's own **Users**
section (role and managed city), so Django's default *Authentication and
Authorization* group editor is hidden from the admin index and from the
navigation. Nothing is unregistered: the model stays in the registry and
``/admin/auth/group/`` still opens for a superuser who needs it, and Django's
own permission checks are untouched.
"""
from django.contrib import admin

_base_get_app_list = admin.site.get_app_list


def _get_app_list_without_auth(request, app_label=None):
    """Hide the ``auth`` application from the admin app list."""
    app_list = _base_get_app_list(request, app_label)
    return [app for app in app_list if app.get("app_label") != "auth"]


admin.site.get_app_list = _get_app_list_without_auth
