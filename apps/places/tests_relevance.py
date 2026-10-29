"""Tests for the relevance feedback on a recommended destination."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.cities.models import City
from apps.info.models import RecommendationRating
from .models import Place


class RelevanceRatingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.city = City.objects.create(
            id=2, name="Kabankalan", slug="kabankalan", province="Negros Occidental",
        )
        cls.place = Place.objects.create(
            city=cls.city, title="Mag Aso Falls", slug="mag-aso-falls",
            address="Kabankalan", is_active=True, is_verified=True,
        )
        cls.user = get_user_model().objects.create_user(
            username="rater", password="test-pass"
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.detail_url = reverse("places:place_detail", args=[self.place.pk])
        self.rate_url = reverse("places:rate_relevance", args=[self.place.pk])

    def test_control_is_hidden_without_an_active_search(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_search_query"], "")
        self.assertNotContains(response, "Rate this recommendation")
        self.assertNotContains(response, self.rate_url)

    def test_control_is_shown_for_the_active_search(self):
        session = self.client.session
        session["attraction_search_query"] = "falls"
        session.save()

        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rate this recommendation")
        self.assertContains(response, self.rate_url)
        self.assertContains(response, "falls")

    def test_rating_is_stored_with_the_active_search(self):
        session = self.client.session
        session["attraction_search_query"] = "falls"
        session.save()

        response = self.client.post(self.rate_url, {"rating": "relevant"})
        self.assertRedirects(response, self.detail_url, fetch_redirect_response=False)

        rating = RecommendationRating.objects.get()
        self.assertEqual(rating.user, self.user)
        self.assertEqual(rating.place, self.place)
        self.assertEqual(rating.query_text, "falls")
        self.assertEqual(rating.rating, "relevant")

    def test_rating_can_be_changed_without_duplicating_the_record(self):
        self.client.post(self.rate_url, {"rating": "partial"})
        self.client.post(self.rate_url, {"rating": "irrelevant"})
        self.assertEqual(RecommendationRating.objects.count(), 1)
        self.assertEqual(RecommendationRating.objects.get().rating, "irrelevant")

    def test_explicit_query_text_wins_over_the_session(self):
        self.client.post(
            self.rate_url, {"rating": "relevant", "query_text": "waterfall"}
        )
        self.assertEqual(RecommendationRating.objects.get().query_text, "waterfall")

    def test_unknown_rating_is_rejected(self):
        response = self.client.post(self.rate_url, {"rating": "amazing"})
        self.assertRedirects(response, self.detail_url, fetch_redirect_response=False)
        self.assertEqual(RecommendationRating.objects.count(), 0)

    def test_anonymous_visitors_cannot_rate(self):
        self.client.logout()
        response = self.client.post(self.rate_url, {"rating": "relevant"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])
        self.assertEqual(RecommendationRating.objects.count(), 0)

    def test_get_requests_are_not_allowed(self):
        response = self.client.get(self.rate_url)
        self.assertEqual(response.status_code, 405)
