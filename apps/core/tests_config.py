"""Configuration tests.

The deployment values (secret key, debug flag, allowed hosts, database
credentials and the MapTiler token) must be configurable through the
environment instead of being frozen inside the source or the templates.
"""
import os
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.cities.models import City


class SettingsTests(SimpleTestCase):
    def test_allowed_hosts_are_normalized(self):
        for host in settings.ALLOWED_HOSTS:
            self.assertEqual(host, host.strip())
        # The previous value " 10.172.248.90 " carried stray spaces.
        self.assertIn("10.172.248.90", settings.ALLOWED_HOSTS)
        self.assertNotIn(" 10.172.248.90 ", settings.ALLOWED_HOSTS)

    def test_environment_readers(self):
        from mysite.settings import _env_flag, _env_list

        with mock.patch.dict(os.environ, {"EA_FLAG": "yes", "EA_LIST": " a , b "}):
            self.assertTrue(_env_flag("EA_FLAG"))
            self.assertEqual(_env_list("EA_LIST"), ["a", "b"])
        with mock.patch.dict(os.environ, {"EA_FLAG": "0"}):
            self.assertFalse(_env_flag("EA_FLAG"))
        self.assertFalse(_env_flag("EA_MISSING_FLAG"))
        self.assertEqual(_env_list("EA_MISSING_LIST", default=("x",)), ["x"])

    def test_map_token_is_defined_in_the_settings(self):
        self.assertTrue(settings.MAPTILER_API_KEY)

    def test_only_mysql_receives_the_mysql_connection_options(self):
        from mysite.settings import _database_options

        mysql = _database_options("django.db.backends.mysql")
        self.assertEqual(mysql["charset"], "utf8mb4")
        self.assertIn("sql_mode", mysql["init_command"])

        # The SQLite fallback used for local testing must stay option-free:
        # sqlite3 rejects "charset" as a connection keyword.
        self.assertEqual(_database_options("django.db.backends.sqlite3"), {})


class MapTilerTemplateTests(TestCase):
    """The maps must read the token from the context, not from the HTML."""

    @classmethod
    def setUpTestData(cls):
        City.objects.get_or_create(id=2, defaults={"name": "Kabankalan"})
        cls.visitor = get_user_model().objects.create_user(
            username="config_visitor", password="test-pass"
        )

    def test_templates_do_not_embed_the_token_literal(self):
        templates = (
            Path(settings.BASE_DIR) / "templates" / "places" / "attraction_carousel.html",
            Path(settings.BASE_DIR) / "templates" / "places" / "nearby_places.html",
        )
        for template in templates:
            with self.subTest(template=template.name):
                source = template.read_text(encoding="utf-8")
                self.assertNotIn(settings.MAPTILER_API_KEY, source)
                self.assertIn("{{ MAPTILER_API_KEY", source)

    def test_rendered_map_page_uses_the_configured_token(self):
        self.client.force_login(self.visitor)
        response = self.client.get(reverse("places:attraction_carousel"), {"browse": "all"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, settings.MAPTILER_API_KEY)
