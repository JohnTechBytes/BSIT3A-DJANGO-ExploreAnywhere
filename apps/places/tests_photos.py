"""Licensed photo lookup: matching rules and the Destinations admin actions."""
import os
from unittest import mock

from django.contrib import admin as dj_admin
from django.test import RequestFactory, TestCase

from apps.cities.models import City

from . import photo_enrichment
from .admin import PlaceAdmin
from .models import Place

CANDIDATE = {
    "file_title": "File:Mag-aso waterfalls resort.jpg",
    "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e2/Mag-aso_waterfalls_resort.jpg/960px-x.jpg",
    "source_url": "https://commons.wikimedia.org/wiki/File:Mag-aso_waterfalls_resort.jpg",
    "credit": "Choi2451",
    "license": "CC BY-SA 3.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/3.0",
}


def queries_for(title):
    return (f'"{title}" Kabankalan',)


class MatchingRulesTests(TestCase):
    def test_significant_words_must_all_appear_in_the_file_name(self):
        self.assertTrue(photo_enrichment.title_matches("Mag Aso Falls", "Mag-aso waterfalls resort"))
        self.assertTrue(photo_enrichment.title_matches("Mount Luyang", "Mt Luyang trail, Kabankalan"))
        self.assertFalse(photo_enrichment.title_matches("Mount Luyang", "Mag-aso waterfalls resort"))
        self.assertFalse(photo_enrichment.title_matches("", "anything"))

    def test_only_free_licences_are_accepted(self):
        self.assertTrue(photo_enrichment.licence_is_allowed("CC BY-SA 3.0"))
        self.assertTrue(photo_enrichment.licence_is_allowed("CC0 1.0"))
        self.assertFalse(photo_enrichment.licence_is_allowed("All rights reserved"))
        self.assertFalse(photo_enrichment.licence_is_allowed(""))

    def test_the_first_confident_licensed_candidate_wins(self):
        place = Place(title="Mag Aso Falls")
        licences = [
            dict(CANDIDATE, license="All rights reserved"),
            dict(CANDIDATE, file_title="File:Some other waterfall.jpg"),
            CANDIDATE,
        ]
        candidate, reason = photo_enrichment.find_photo(
            place, search=lambda query, agent, limit: licences, queries_for=queries_for, agent="App/1.0 (a@b.test)")
        self.assertEqual(candidate["credit"], "Choi2451")
        self.assertIn("Matched", reason)

    def test_without_a_user_agent_nothing_is_queried(self):
        place = Place(title="Mag Aso Falls")
        search = mock.Mock()
        with mock.patch.dict(os.environ, {"WIKIMEDIA_USER_AGENT": ""}):
            candidate, reason = photo_enrichment.find_photo(
                place, search=search, queries_for=queries_for, agent="")
        self.assertIsNone(candidate)
        self.assertIn("WIKIMEDIA_USER_AGENT", reason)
        search.assert_not_called()

    def test_a_failing_search_is_reported_not_raised(self):
        place = Place(title="Mag Aso Falls")

        def boom(query, agent, limit):
            raise TimeoutError("network down")

        candidate, reason = photo_enrichment.find_photo(
            place, search=boom, queries_for=queries_for, agent="App/1.0 (a@b.test)")
        self.assertIsNone(candidate)
        self.assertIn("Search failed", reason)

    def test_no_match_lists_the_candidates_it_checked(self):
        place = Place(title="CPSU Museum")
        candidate, reason = photo_enrichment.find_photo(
            place, search=lambda q, a, l: [CANDIDATE], queries_for=queries_for, agent="App/1.0 (a@b.test)")
        self.assertIsNone(candidate)
        self.assertIn("No confident match", reason)


class CommonsAdminActionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.city = City.objects.create(pk=2, name="Kabankalan", slug="kabankalan",
                                       province="Negros Occidental")
        cls.place = Place.objects.create(
            city=cls.city, title="Mag Aso Falls", slug="mag-aso-falls",
            address="Kabankalan", is_active=True, is_verified=True,
        )
        cls.with_photo = Place.objects.create(
            city=cls.city, title="Mag Aso Falls Resort", slug="mag-aso-falls-resort",
            address="Kabankalan", is_active=True, is_verified=True,
            cover_image_url="https://upload.wikimedia.org/existing.jpg",
            photo_credit="Existing",
        )

    def setUp(self):
        self.model_admin = PlaceAdmin(Place, dj_admin.site)
        self.request = RequestFactory().get("/admin/places/place/")
        self.queryset = Place.objects.all()
        self.env = mock.patch.dict(os.environ, {"WIKIMEDIA_USER_AGENT": "ExploreKabankalan/1.0 (test@example.test)"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_preview_reports_matches_without_writing(self):
        with mock.patch.object(PlaceAdmin, "message_user") as message_user, \
             mock.patch.object(PlaceAdmin, "_commons_helpers",
                               return_value=(lambda q, a, l: [CANDIDATE], queries_for)):
            self.model_admin.preview_commons_photos(self.request, self.queryset)

        self.place.refresh_from_db()
        self.assertEqual(self.place.cover_image_url, "")
        self.assertEqual(self.place.photo_credit, "")
        sent = " ".join(str(call.args[1]) for call in message_user.call_args_list)
        self.assertIn("licensed, name-matched photo", sent)

    def test_attach_writes_photo_and_credit_but_never_overwrites(self):
        with mock.patch.object(PlaceAdmin, "message_user"), \
             mock.patch.object(PlaceAdmin, "_commons_helpers",
                               return_value=(lambda q, a, l: [CANDIDATE], queries_for)):
            self.model_admin.attach_commons_photos(self.request, self.queryset)

        self.place.refresh_from_db()
        self.assertEqual(self.place.cover_image_url, CANDIDATE["image_url"])
        self.assertEqual(self.place.photo_credit, "Choi2451")
        self.assertEqual(self.place.photo_license, "CC BY-SA 3.0")
        self.assertEqual(self.place.photo_source_url, CANDIDATE["source_url"])
        self.assertEqual(self.place.photo_license_url, CANDIDATE["license_url"])

        self.with_photo.refresh_from_db()
        self.assertEqual(self.with_photo.cover_image_url, "https://upload.wikimedia.org/existing.jpg")
        self.assertEqual(self.with_photo.photo_credit, "Existing")

    def test_actions_explain_a_missing_user_agent_instead_of_failing(self):
        with mock.patch.dict(os.environ, {"WIKIMEDIA_USER_AGENT": ""}), \
             mock.patch.object(PlaceAdmin, "message_user") as message_user:
            self.model_admin.attach_commons_photos(self.request, self.queryset)

        self.place.refresh_from_db()
        self.assertEqual(self.place.cover_image_url, "")
        sent = " ".join(str(call.args[1]) for call in message_user.call_args_list)
        self.assertIn("WIKIMEDIA_USER_AGENT", sent)
