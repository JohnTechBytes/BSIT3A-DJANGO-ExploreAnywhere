from django.test import RequestFactory, SimpleTestCase, TestCase
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

    def test_published_osm_records_are_prioritized_and_attributed(self):
        osm = Place.objects.create(
            city=self.city, title="Published OSM discovery", slug="osm-node-12345",
            address="Kabankalan", is_verified=True, is_active=True,
        )
        response = self.render_home()
        self.assertContains(response, osm.title)
        self.assertContains(response, "https://www.openstreetmap.org/node/12345")
        self.assertContains(response, "OpenStreetMap contributors")
        self.assertLess(response.content.index(osm.title.encode()),
                        response.content.index(self.place.title.encode()))

    def test_unpublished_osm_record_is_not_exposed(self):
        Place.objects.create(city=self.city, title="Private OSM record",
                             slug="osm-way-123", address="Local", is_verified=False)
        self.assertNotContains(self.render_home(), "Private OSM record")
        self.assertNotContains(self.render_home(), "openstreetmap.org/way/123")

    def test_invalid_osm_slug_never_becomes_source_link(self):
        self.place.slug = 'osm-node-123/invalid'
        self.place.save()
        self.assertNotContains(self.render_home(), 'openstreetmap.org/node/123')

    def test_photographed_osm_record_is_featured_first(self):
        Place.objects.create(city=self.city, title="OSM without photo", slug="osm-node-1",
                             address="Local", is_verified=True, avg_rating=5)
        photo = Place.objects.create(
            city=self.city, title="OSM with photo", slug="osm-way-2", address="Local",
            is_verified=True, cover_image_url="https://example.com/place.jpg",
        )
        response = self.render_home()
        self.assertContains(response, photo.cover_image_url)
        self.assertLess(response.content.index(b'OSM with photo'),
                        response.content.index(b'OSM without photo'))

    def test_missing_nature_photo_uses_labeled_sample(self):
        response = self.render_home()
        self.assertContains(response, 'img/samples/nature.jpg')
        self.assertContains(response, 'AI-generated category sample')
        self.assertContains(response, 'not an actual photo of Existing local place')

    def test_real_photo_always_takes_priority_over_sample(self):
        self.place.cover_image_url = 'https://example.com/real-photo.jpg'
        self.place.save()
        response = self.render_home()
        self.assertContains(response, self.place.cover_image_url)
        self.assertNotContains(response, 'img/samples/nature.jpg')
        self.assertNotContains(response, 'AI-generated category sample')

    def test_samples_match_category_and_do_not_guess_unknown_venues(self):
        from .views import sample_image_for
        self.place.category = None
        for title, expected in [
            ('Local Waterfalls', 'nature'), ('Local Inasal Grill', 'food'),
            ('City Plaza', 'city'), ('Billiards Hall', 'billiards'), ('Book Shop', ''),
        ]:
            self.place.title = title
            self.assertEqual(sample_image_for(self.place),
                             f'img/samples/{expected}.jpg' if expected else '')


class ErrorPageTests(SimpleTestCase):
    """The custom 404/500 handlers must render the dark error screens."""

    def test_error_page_views_use_the_shared_design(self):
        from .views import error_404, error_500

        not_found = error_404(RequestFactory().get("/missing/"))
        self.assertEqual(not_found.status_code, 404)
        self.assertIn(b"ERROR 404", not_found.content)
        self.assertIn(b"css/error.css", not_found.content)

        server_error = error_500(RequestFactory().get("/boom/"))
        self.assertEqual(server_error.status_code, 500)
        self.assertIn(b"ERROR 500", server_error.content)
        self.assertIn(b"ExploreKabankalan", server_error.content)

    def test_custom_handlers_are_wired(self):
        from mysite import urls

        self.assertEqual(urls.handler404, "mysite.views.error_404")
        self.assertEqual(urls.handler500, "mysite.views.error_500")
