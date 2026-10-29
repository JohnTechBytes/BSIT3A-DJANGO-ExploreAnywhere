"""Legacy account routes kept for links published before the redesign.

The canonical branded sign-in lives under ``/accounts/`` (see ``auth_urls.py``).
These aliases keep ``/users/login/`` and ``/users/logout/`` working, but they
no longer own the ``login`` / ``logout`` URL names so that ``reverse("login")``
always resolves to the branded :class:`ExploreLoginView`.
"""
from django.urls import path

from .auth_views import ExploreLoginView, ExploreLogoutView

urlpatterns = [
    path("login/", ExploreLoginView.as_view(), name="legacy_login"),
    path("logout/", ExploreLogoutView.as_view(), name="legacy_logout"),
]
