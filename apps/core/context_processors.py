"""Template context shared by every ExploreAnywhere page.

Keeping the deployment configuration here (instead of hard-coding it inside a
template) means the MapTiler access token can be rotated through an
environment variable without editing the HTML.
"""
from django.conf import settings


def explore_settings(request):
    """Expose the configuration values the templates need."""
    return {
        "MAPTILER_API_KEY": getattr(settings, "MAPTILER_API_KEY", ""),
    }
