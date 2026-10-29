"""Tests for the public usability evaluation (System Usability Scale) module."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.cities.models import City
from apps.info.models import SusResponse


def answers(positive, negative):
    """The ten SUS answers: the odd items get one value, the even items another."""
    return {
        f"q{index}": positive if index % 2 else negative
        for index in range(1, 11)
    }


class SusSurveyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        City.objects.get_or_create(id=2, defaults={"name": "Kabankalan"})
        cls.user = get_user_model().objects.create_user(
            username="sus_user", password="test-pass"
        )

    def test_survey_page_is_public_and_shows_the_ten_items(self):
        response = self.client.get(reverse("evaluation:sus_survey"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "evaluation/sus_form.html")
        self.assertContains(response, "System Usability Scale")
        self.assertContains(response, "I think that I would like to use this system frequently")
        # Ten statements, each with five radio answers.
        self.assertEqual(len(response.context["form"].fields), 10)
        self.assertContains(response, 'name="q1"')
        self.assertContains(response, 'name="q10"')

    def test_survey_requires_every_item(self):
        response = self.client.post(reverse("evaluation:sus_survey"), {"q1": "4"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SusResponse.objects.count(), 0)
        self.assertTrue(response.context["form"].errors)

    def test_completed_survey_stores_the_response_and_redirects(self):
        response = self.client.post(
            reverse("evaluation:sus_survey"), answers("4", "4")
        )
        self.assertRedirects(response, reverse("evaluation:sus_thanks"), fetch_redirect_response=False)

        stored = SusResponse.objects.get()
        self.assertEqual(stored.user, None)
        # Every answer is 4: the odd items score 3 and the even items score 1,
        # so the SUS score is (15 + 5) * 2.5 = 50.
        self.assertEqual(float(stored.score), 50.0)

    def test_signed_in_visitor_response_is_linked_to_the_account(self):
        self.client.force_login(self.user)
        self.client.post(reverse("evaluation:sus_survey"), answers("5", "1"))
        stored = SusResponse.objects.get()
        self.assertEqual(stored.user, self.user)
        # Best possible pattern: the odd items score 4 and the even items 4,
        # so the SUS score is (20 + 20) * 2.5 = 100.
        self.assertEqual(float(stored.score), 100.0)

    def test_result_page_shows_the_score_and_the_answers(self):
        self.client.post(reverse("evaluation:sus_survey"), answers("5", "1"))
        response = self.client.get(reverse("evaluation:sus_thanks"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "evaluation/thank_you.html")
        self.assertContains(response, "100.0")
        self.assertContains(response, "Excellent")
        self.assertEqual(len(response.context["answers"]), 10)

    def test_result_page_without_a_response_is_honest(self):
        response = self.client.get(reverse("evaluation:sus_thanks"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No survey answer yet")

    def test_low_score_is_reported_honestly(self):
        self.client.post(reverse("evaluation:sus_survey"), answers("1", "5"))
        response = self.client.get(reverse("evaluation:sus_thanks"))
        self.assertContains(response, "Awful")
        self.assertContains(response, "0.0")

    def test_survey_is_reachable_from_the_footer_and_navigation(self):
        response = self.client.get(reverse("evaluation:sus_survey"))
        self.assertContains(response, "Usability Survey")
        self.assertContains(response, reverse("evaluation:sus_survey"))
