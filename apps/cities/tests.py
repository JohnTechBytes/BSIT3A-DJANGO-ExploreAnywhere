from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .locking import locked_cities
from .models import City, Province


class CityLockingTests(TestCase):
    """The site serves Kabankalan only, so nothing may offer another city."""

    def setUp(self):
        self.province = Province.objects.create(
            name="Negros Occidental",
            slug="negros-occidental",
            region="Western Visayas",
            region_code="06",
            psgc_code="0604500000",
        )
        self.kabankalan = City.objects.create(
            id=2,
            name="Kabankalan",
            slug="kabankalan",
            province="Negros Occidental",
            province_ref=self.province,
            latitude="9.990000",
            longitude="122.810000",
        )
        # A second city with coordinates, to prove it is not offered.
        self.other = City.objects.create(
            name="Dumaguete",
            slug="dumaguete",
            province="Negros Oriental",
            latitude="9.310000",
            longitude="123.300000",
        )
        self.user = get_user_model().objects.create_user(
            username="tester", password="secret123"
        )
        self.client.force_login(self.user)

    def test_locked_cities_returns_only_kabankalan(self):
        ids = list(locked_cities().values_list("pk", flat=True))
        self.assertEqual(ids, [self.kabankalan.pk])

    def test_choosing_another_city_is_rejected(self):
        response = self.client.post(
            reverse("city_choose"),
            {"city_id": str(self.other.pk)},
        )

        self.assertRedirects(
            response,
            reverse("city_selection"),
            fetch_redirect_response=False,
        )
        self.assertEqual(
            self.client.session["selected_city_id"], self.kabankalan.pk
        )

    def test_choosing_kabankalan_succeeds(self):
        response = self.client.post(
            reverse("city_choose"),
            {"city_id": str(self.kabankalan.pk)},
        )

        self.assertRedirects(
            response,
            reverse("places:city_discover"),
            fetch_redirect_response=False,
        )
        self.assertEqual(
            self.client.session["selected_city_id"], self.kabankalan.pk
        )

    def test_middleware_repins_a_tampered_session(self):
        session = self.client.session
        session["city_id"] = self.other.pk
        session["selected_city_id"] = self.other.pk
        session["selected_city_name"] = self.other.name
        session["selected_province"] = self.other.province
        session.save()

        self.client.get(reverse("home"))

        self.assertEqual(
            self.client.session["selected_city_id"], self.kabankalan.pk
        )
        self.assertEqual(
            self.client.session["selected_city_name"], "Kabankalan"
        )

    def test_api_provinces_exposes_only_the_locked_province(self):
        payload = self.client.get(reverse("api_provinces")).json()

        self.assertEqual(
            [p["slug"] for p in payload["provinces"]],
            [self.province.slug],
        )

    def test_api_cities_exposes_only_the_locked_city(self):
        payload = self.client.get(
            reverse("api_cities"), {"province": self.province.slug}
        ).json()

        self.assertEqual(
            [c["name"] for c in payload["cities"]],
            ["Kabankalan"],
        )
        self.assertEqual(payload["total"], 1)

    def test_api_cities_returns_nothing_for_another_province(self):
        payload = self.client.get(
            reverse("api_cities"), {"province": "negros-oriental"}
        ).json()

        self.assertEqual(payload["cities"], [])
        self.assertEqual(payload["total"], 0)
