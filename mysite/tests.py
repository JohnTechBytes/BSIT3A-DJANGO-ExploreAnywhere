from django.test import RequestFactory, TestCase
from django.contrib.auth.models import AnonymousUser

from apps.cities.models import City
from apps.core.models import Category
from apps.places.models import Place
from .views import home


class HomepageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.city = City.objects.create(pk=2, name="Kabankalan", slug="kabankalan")
        cls.other_city = City.objects.create(name="Other City", slug="other-city")
        cls.category = Category.objects.create(name="Nature", slug="nature")
        cls.place = Place.objects.create(
            city=cls.city, title="Existing local place", address="Kabankalan",
            category=cls.category, is_verified=True, is_active=True,
            description="Existing description", avg_rating=4.5, review_count=3,
        )
        Place.objects.create(city=cls.city, title="Unverified place", address="Local")
        Place.objects.create(city=cls.city, title="Inactive place", address="Local",
                             is_verified=True, is_active=False)
        Place.objects.create(city=cls.other_city, title="Outside city", address="Other",
                             is_verified=True)

    def render_home(self, query=None):
        request = RequestFactory().get("/", query or {})
        request.user = AnonymousUser()
        return home(request)

    def test_existing_published_content_only(self):
        response = self.render_home()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Existing local place")
        self.assertContains(response, "Existing description")
        self.assertContains(response, "4.5")
        self.assertNotContains(response, "Unverified place")
        self.assertNotContains(response, "Inactive place")
        self.assertNotContains(response, "Outside city")

    def test_category_filter(self):
        self.assertContains(self.render_home({"category": "nature"}), "Existing local place")
        response = self.render_home({"category": "missing"})
        self.assertNotContains(response, "Existing local place")
        self.assertContains(response, "No places in this category yet.")
        self.assertContains(response, "Nature")

    def test_empty_database_does_not_invent_destinations(self):
        Place.objects.all().delete()
        response = self.render_home()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Find your kind of local adventure.")
        self.assertContains(response, "landing-background.webp")

    def test_content_is_escaped(self):
        self.place.title = '<script>alert("test")</script>'
        self.place.save()
        response = self.render_home()
        self.assertNotContains(response, '<script>alert("test")</script>')
        self.assertContains(response, "&lt;script&gt;")
