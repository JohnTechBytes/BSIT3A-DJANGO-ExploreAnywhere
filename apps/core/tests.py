from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.cities.models import City


class HomeViewTests(TestCase):
    """The home page is the public entry point for the site.

    KabankalanOnlyMiddleware resolves the locked city on the first request and
    raises ImproperlyConfigured if it is missing, so every request in these
    tests needs that row to exist.
    """

    def setUp(self):
        City.objects.create(id=2, name="Kabankalan", province="Negros Occidental")

    def test_home_renders_for_authenticated_user(self):
        user = get_user_model().objects.create_user(username="admin", password="secret1234")

        self.client.force_login(user)
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")

    def test_home_is_public_for_anonymous_visitors(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")
