from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase

from .models import SearchResult, SearchResultLocation, SearchTopic, SourceScope
from .result_locations import (
    build_location_signature,
    extract_location_candidates,
    refresh_result_locations,
)
from .test_helpers import CloudflareAccessTestMixin


class OwnedTestCase(CloudflareAccessTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username=f"user-{self.__class__.__name__.lower()}",
            email=f"{self.__class__.__name__.lower()}@example.com",
            password="secret123",
        )
        self.other_user = user_model.objects.create_user(
            username=f"other-{self.__class__.__name__.lower()}",
            email=f"other-{self.__class__.__name__.lower()}@example.com",
            password="secret123",
        )
        self.set_cloudflare_identity(user=self.user)

    def create_topic(self, user, name="Topic"):
        return SearchTopic.objects.create(
            owner=user,
            name=name,
            queries=[f"{name.lower()} query"],
        )

    def create_source(self, user, name="Source"):
        return SourceScope.objects.create(
            owner=user,
            name=name,
            kind=SourceScope.Kind.PUBLIC,
        )

    def create_result(self, topic, source_scope, title, url):
        return SearchResult.objects.create(
            topic=topic,
            source_scope=source_scope,
            title=title,
            url=url,
            normalized_url=url,
            domain="example.com",
            snippet="A short preview.",
            matched_queries=["query"],
        )


class LocationCandidateExtractionTests(TestCase):
    def test_extract_location_candidates_finds_contextual_and_comma_places(self):
        candidates = extract_location_candidates(
            title="Officials in Zurich brace for more rain",
            snippet=(
                "Emergency crews from Bern responded overnight while talks in "
                "Geneva, Switzerland resumed this morning."
            ),
        )

        self.assertIn("Zurich", candidates)
        self.assertIn("Bern", candidates)
        self.assertIn("Geneva, Switzerland", candidates)


class SearchResultLocationStorageTests(OwnedTestCase):
    @patch("core.result_locations.extract_location_candidates", return_value=["Zurich", "Bern"])
    @patch("core.result_locations.geocode_location_candidate")
    def test_refresh_result_locations_stores_multiple_places(
        self,
        geocode_mock,
        _extract_mock,
    ):
        topic = self.create_topic(self.user, name="Floods")
        source = self.create_source(self.user, name="News")
        result = self.create_result(
            topic=topic,
            source_scope=source,
            title="Flood updates",
            url="https://example.com/flood-updates",
        )

        geocode_mock.side_effect = lambda candidate: {
            "name": candidate,
            "normalized_name": candidate.lower(),
            "display_name": f"{candidate}, Switzerland",
            "latitude": "47.376900" if candidate == "Zurich" else "46.948000",
            "longitude": "8.541700" if candidate == "Zurich" else "7.447400",
            "place_type": "city",
            "importance": 0.8,
        }

        locations = refresh_result_locations(result)
        result.refresh_from_db()

        self.assertEqual(result.location_signature, build_location_signature(result))
        self.assertEqual(result.locations.count(), 2)
        self.assertEqual({location.name for location in locations}, {"Zurich", "Bern"})

        geocode_mock.reset_mock()
        refreshed_locations = refresh_result_locations(result)

        geocode_mock.assert_not_called()
        self.assertEqual(len(refreshed_locations), 2)


class SearchResultMapApiTests(OwnedTestCase):
    def test_results_map_aggregates_related_messages_per_location(self):
        topic = self.create_topic(self.user, name="Europe Watch")
        source = self.create_source(self.user, name="Public")
        other_topic = self.create_topic(self.other_user, name="Other User Topic")
        other_source = self.create_source(self.other_user, name="Other Source")

        first_result = self.create_result(
            topic=topic,
            source_scope=source,
            title="Zurich update",
            url="https://example.com/zurich-update",
        )
        second_result = self.create_result(
            topic=topic,
            source_scope=source,
            title="Bern and Zurich update",
            url="https://example.com/bern-zurich-update",
        )
        hidden_result = self.create_result(
            topic=other_topic,
            source_scope=other_source,
            title="Hidden result",
            url="https://example.com/hidden-result",
        )

        SearchResultLocation.objects.bulk_create(
            [
                SearchResultLocation(
                    result=first_result,
                    name="Zurich",
                    normalized_name="zurich",
                    display_name="Zurich, Switzerland",
                    latitude=Decimal("47.376900"),
                    longitude=Decimal("8.541700"),
                    place_type="city",
                ),
                SearchResultLocation(
                    result=second_result,
                    name="Zurich",
                    normalized_name="zurich",
                    display_name="Zurich, Switzerland",
                    latitude=Decimal("47.376900"),
                    longitude=Decimal("8.541700"),
                    place_type="city",
                ),
                SearchResultLocation(
                    result=second_result,
                    name="Bern",
                    normalized_name="bern",
                    display_name="Bern, Switzerland",
                    latitude=Decimal("46.948000"),
                    longitude=Decimal("7.447400"),
                    place_type="city",
                ),
                SearchResultLocation(
                    result=hidden_result,
                    name="Paris",
                    normalized_name="paris",
                    display_name="Paris, France",
                    latitude=Decimal("48.856600"),
                    longitude=Decimal("2.352200"),
                    place_type="city",
                ),
            ]
        )

        response = self.client.get("/api/v1/results/map/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["result_count"], 2)
        self.assertEqual(payload["mapped_result_count"], 2)
        self.assertEqual(payload["location_count"], 2)

        markers = {marker["name"]: marker for marker in payload["markers"]}
        self.assertEqual(markers["Zurich"]["related_result_count"], 2)
        self.assertEqual(markers["Bern"]["related_result_count"], 1)
        self.assertEqual(
            {item["title"] for item in markers["Zurich"]["results"]},
            {"Zurich update", "Bern and Zurich update"},
        )


class SearchResultLocationCommandTests(OwnedTestCase):
    @patch("core.management.commands.backfill_result_locations.refresh_result_locations")
    def test_backfill_command_refreshes_existing_results(self, refresh_mock):
        topic = self.create_topic(self.user, name="Command Topic")
        source = self.create_source(self.user, name="Command Source")
        self.create_result(
            topic=topic,
            source_scope=source,
            title="Zurich command result",
            url="https://example.com/command-result",
        )

        refresh_mock.return_value = []
        stdout = StringIO()

        call_command("backfill_result_locations", stdout=stdout)

        refresh_mock.assert_called_once()
        self.assertIn("Processed 1 results", stdout.getvalue())
