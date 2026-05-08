from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import httpx
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test import override_settings
from django.utils import timezone

from .models import SearchProviderConfig, SearchResult, SearchTopic, SourceScope
from .services import (
    build_direct_searxng_params,
    build_search_query,
    build_searxng_params,
    load_searxng_engines,
    load_searxng_language_options,
    normalize_searxng_engines,
    normalize_searxng_language,
    run_direct_searxng_search,
    sort_search_items,
)
from .tasks import dispatch_due_topic_searches


class QueryBuilderTests(TestCase):
    def test_build_search_query_adds_required_and_excluded_terms(self):
        query = build_search_query(
            base_query='"research data exchange"',
            required_terms=["metadata schema", "open data"],
            excluded_terms=["jobs", "consulting"],
        )

        self.assertIn('"research data exchange"', query)
        self.assertIn('"metadata schema"', query)
        self.assertIn('"open data"', query)
        self.assertIn('-jobs', query)
        self.assertIn('-consulting', query)


class OwnedTestCase(TestCase):
    def setUp(self):
        super().setUp()
        User = get_user_model()
        self.user = User.objects.create_user(
            username=f"user-{self.__class__.__name__.lower()}",
            email=f"{self.__class__.__name__.lower()}@example.com",
            password="secret123",
        )


class ModelDefaultsTests(OwnedTestCase):
    def test_provider_config_load_creates_default_singleton(self):
        config = SearchProviderConfig.load()

        self.assertEqual(config.name, "searxng")
        self.assertTrue(config.enabled)

    def test_topic_slug_is_generated(self):
        topic = SearchTopic.objects.create(
            owner=self.user,
            name="Research Data Exchange Landscape",
            queries=["research data exchange"],
        )
        self.assertEqual(topic.slug, "research-data-exchange-landscape")
        self.assertEqual(topic.schedule_every, 1)
        self.assertEqual(topic.schedule_unit, SearchTopic.ScheduleUnit.DAYS)
        self.assertIsNotNone(topic.next_run_at)

    def test_topic_can_link_to_sources(self):
        source = SourceScope.objects.create(
            owner=self.user, name="Research", kind=SourceScope.Kind.RESEARCH
        )
        topic = SearchTopic.objects.create(
            owner=self.user, name="Data Platforms", queries=["data platform"]
        )
        topic.source_scopes.add(source)

        self.assertEqual(topic.source_scopes.count(), 1)

    def test_source_scope_supports_searxng_categories(self):
        source = SourceScope.objects.create(
            owner=self.user,
            name="Public",
            kind=SourceScope.Kind.PUBLIC,
            searxng_categories=["general", "news"],
            time_range=SourceScope.TimeRange.AUTO,
        )

        self.assertEqual(source.searxng_categories, ["general", "news"])
        self.assertTrue(source.use_all_categories)
        self.assertTrue(source.use_all_engines)
        self.assertEqual(source.result_order, SourceScope.ResultOrder.RELEVANCE)

    def test_topic_schedule_updates_next_run_when_changed(self):
        topic = SearchTopic.objects.create(
            owner=self.user,
            name="Weekly Exchange Scan",
            queries=["research data exchange"],
        )
        original_next_run = topic.next_run_at

        topic.schedule_every = 2
        topic.schedule_unit = SearchTopic.ScheduleUnit.HOURS
        topic.save()
        topic.refresh_from_db()

        self.assertGreater(topic.next_run_at, timezone.now())
        self.assertNotEqual(topic.next_run_at, original_next_run)
        self.assertEqual(topic.schedule_description, "Every 2 hours")

    def test_disabling_topic_clears_next_run(self):
        topic = SearchTopic.objects.create(
            owner=self.user,
            name="Paused Topic",
            queries=["data platform"],
        )

        topic.enabled = False
        topic.save()
        topic.refresh_from_db()

        self.assertIsNone(topic.next_run_at)


class SchedulerTaskTests(OwnedTestCase):
    @patch("core.tasks.run_topic_search_task.delay")
    def test_dispatch_due_topic_searches_queues_only_due_topics(self, delay_mock):
        due_topic = SearchTopic.objects.create(
            owner=self.user,
            name="Due Topic",
            queries=["research data exchange"],
            schedule_every=15,
            schedule_unit=SearchTopic.ScheduleUnit.MINUTES,
        )
        future_topic = SearchTopic.objects.create(
            owner=self.user,
            name="Future Topic",
            queries=["data platform"],
            schedule_every=1,
            schedule_unit=SearchTopic.ScheduleUnit.DAYS,
        )
        due_topic.next_run_at = timezone.now() - timedelta(minutes=1)
        due_topic.save(update_fields=["next_run_at", "updated_at"])
        future_topic.next_run_at = timezone.now() + timedelta(hours=1)
        future_topic.save(update_fields=["next_run_at", "updated_at"])

        summary = dispatch_due_topic_searches()
        due_topic.refresh_from_db()
        future_topic.refresh_from_db()

        delay_mock.assert_called_once_with(due_topic.pk)
        self.assertEqual(summary["queued_count"], 1)
        self.assertIn(due_topic.pk, summary["queued_topic_ids"])
        self.assertGreater(due_topic.next_run_at, timezone.now())
        self.assertGreater(future_topic.next_run_at, due_topic.next_run_at - timedelta(hours=1))


class DirectSearxNGSearchTests(OwnedTestCase):
    @patch("core.services.load_searxng_categories", return_value=["general", "science", "news"])
    def test_build_searxng_params_uses_all_categories_by_default(self, _categories_mock):
        topic = SearchTopic.objects.create(
            owner=self.user,
            name="All Categories Topic",
            queries=["research data exchange"],
        )
        source = SourceScope.objects.create(
            owner=self.user,
            name="All Categories Scope",
            kind=SourceScope.Kind.PUBLIC,
            searxng_categories=["general"],
            use_all_categories=True,
        )

        params = build_searxng_params(topic, source, '"research data exchange"')

        self.assertEqual(params["categories"], "general,science,news")

    def test_build_searxng_params_can_restrict_categories_when_requested(self):
        topic = SearchTopic.objects.create(
            owner=self.user,
            name="Restricted Categories Topic",
            queries=["research data exchange"],
        )
        source = SourceScope.objects.create(
            owner=self.user,
            name="Restricted Categories Scope",
            kind=SourceScope.Kind.PUBLIC,
            searxng_categories=["science", "files"],
            use_all_categories=False,
        )

        params = build_searxng_params(topic, source, '"research data exchange"')

        self.assertEqual(params["categories"], "science,files")

    def test_build_searxng_params_uses_all_engines_by_default(self):
        topic = SearchTopic.objects.create(
            owner=self.user,
            name="All Engines Topic",
            queries=["research data exchange"],
        )
        source = SourceScope.objects.create(
            owner=self.user,
            name="All Engines Scope",
            kind=SourceScope.Kind.PUBLIC,
            searxng_categories=["general"],
            use_all_categories=False,
            searxng_engines=["google", "duckduckgo"],
            use_all_engines=True,
        )

        params = build_searxng_params(topic, source, '"research data exchange"')

        self.assertEqual(params["categories"], "general")
        self.assertNotIn("engines", params)

    def test_build_searxng_params_can_restrict_engines_when_requested(self):
        topic = SearchTopic.objects.create(
            owner=self.user,
            name="Restricted Engines Topic",
            queries=["research data exchange"],
        )
        source = SourceScope.objects.create(
            owner=self.user,
            name="Restricted Engines Scope",
            kind=SourceScope.Kind.PUBLIC,
            searxng_engines=["google", "arxiv"],
            use_all_engines=False,
        )

        params = build_searxng_params(topic, source, '"research data exchange"')

        self.assertEqual(params["engines"], "google,arxiv")

    @patch(
        "core.services.load_searxng_config",
        return_value={
            "engines": [
                {"name": "google", "enabled": True},
                {"name": "duckduckgo", "enabled": True},
                {"name": "bing", "enabled": False},
            ]
        },
    )
    def test_load_searxng_engines_returns_enabled_engine_names(self, _config_mock):
        self.assertEqual(load_searxng_engines(), ["duckduckgo", "google"])

    @patch("core.services.load_searxng_engines", return_value=["duckduckgo", "google"])
    def test_normalize_searxng_engines_matches_available_engine_names(self, _engines_mock):
        self.assertEqual(
            normalize_searxng_engines(["Google", "duckduckgo", "google"]),
            ["google", "duckduckgo"],
        )

    @patch("core.services.load_searxng_locales", return_value={"en": "English", "de": "Deutsch"})
    def test_build_searxng_params_normalizes_language_to_available_locale(self, _locales_mock):
        topic = SearchTopic.objects.create(
            owner=self.user,
            name="Language Normalization Topic",
            queries=["research data exchange"],
        )
        source = SourceScope.objects.create(
            owner=self.user,
            name="Language Scope",
            kind=SourceScope.Kind.PUBLIC,
            language="en-US",
        )

        params = build_searxng_params(topic, source, '"research data exchange"')

        self.assertEqual(params["language"], "en")

    def test_build_direct_searxng_params_omits_engines_when_using_all_engines(self):
        params = build_direct_searxng_params(
            {
                "q": '"research data exchange format"',
                "use_all_categories": False,
                "categories": ["general"],
                "use_all_engines": True,
                "engines": ["google", "arxiv"],
            }
        )

        self.assertEqual(params["categories"], "general")
        self.assertNotIn("engines", params)

    def test_sort_search_items_can_order_by_newest_first(self):
        ordered = sort_search_items(
            [
                {"title": "Older", "published_at": "2025-01-01T00:00:00Z", "score": 0.99},
                {"title": "Newest", "published_at": "2025-06-01T00:00:00Z", "score": 0.1},
                {"title": "Undated", "score": 1.0},
            ],
            SourceScope.ResultOrder.NEWEST,
        )

        self.assertEqual([item["title"] for item in ordered], ["Newest", "Older", "Undated"])

    def test_sort_search_items_can_order_by_relevance(self):
        ordered = sort_search_items(
            [
                {"title": "Low", "score": 0.2},
                {"title": "High", "score": 0.95},
                {"title": "Middle", "score": 0.5},
            ],
            SourceScope.ResultOrder.RELEVANCE,
        )

        self.assertEqual([item["title"] for item in ordered], ["High", "Middle", "Low"])

    @patch("core.services.load_searxng_categories", return_value=["general", "science", "news"])
    def test_build_direct_searxng_params_uses_all_categories_by_default(self, _categories_mock):
        params = build_direct_searxng_params(
            {
                "q": '"research data exchange format"',
                "use_all_categories": True,
                "categories": ["general"],
            }
        )

        self.assertEqual(params["categories"], "general,science,news")

    @patch("core.services.load_searxng_locales", return_value={"en": "English", "de": "Deutsch"})
    def test_build_direct_searxng_params_normalizes_language_to_available_locale(
        self, _locales_mock
    ):
        params = build_direct_searxng_params(
            {
                "q": '"research data exchange format"',
                "language": "en-US",
            }
        )

        self.assertEqual(params["language"], "en")

    @patch(
        "core.services.load_searxng_locales",
        return_value={"de": "Deutsch", "en": "English"},
    )
    def test_load_searxng_language_options_returns_sorted_choices(self, _locales_mock):
        self.assertEqual(
            load_searxng_language_options(),
            [
                {"code": "de", "label": "Deutsch"},
                {"code": "en", "label": "English"},
            ],
        )

    @patch("core.services.load_searxng_locales", return_value={"en": "English", "el-GR": "Greek"})
    def test_normalize_searxng_language_matches_case_and_base_language(self, _locales_mock):
        self.assertEqual(normalize_searxng_language("EL-gr"), "el-GR")
        self.assertEqual(normalize_searxng_language("en-US"), "en")

    @override_settings(SEARXNG_BASE_URL="http://searxng:8080", SEARXNG_TIMEOUT_S=5)
    @patch("core.services.load_searxng_locales", return_value={"en": "English"})
    @patch("core.services.SearxNGClient.search")
    def test_run_direct_searxng_search_filters_domains_and_keeps_extra_params(
        self,
        search_mock,
        _locales_mock,
    ):
        SearchProviderConfig.load()
        search_mock.return_value = {
            "number_of_results": 2,
            "suggestions": ["metadata exchange"],
            "answers": [],
            "corrections": [],
            "infoboxes": [],
            "unresponsive_engines": ["duckduckgo"],
            "results": [
                {
                    "title": "Research data exchange format",
                    "url": "https://example.org/formats/spec",
                    "content": "Specification overview",
                    "engine": "google",
                    "engines": ["google", "arxiv"],
                    "score": 0.92,
                },
                {
                    "title": "Blocked domain",
                    "url": "https://jobs.example.com/posting",
                    "content": "Should be excluded",
                    "engine": "google",
                },
            ],
        }

        payload = {
            "q": '"research data exchange format"',
            "use_all_categories": False,
            "categories": ["general", "science"],
            "use_all_engines": False,
            "engines": ["google", "arxiv"],
            "language": "en-US",
            "safesearch": 0,
            "time_range": "month",
            "result_order": "newest",
            "pageno": 2,
            "max_results": 5,
            "include_domains": ["example.org"],
            "exclude_domains": ["jobs.example.com"],
            "extra_params": {
                "theme": "simple",
                "image_proxy": True,
            },
        }

        response = run_direct_searxng_search(payload)
        sent_params = search_mock.call_args.args[0]

        self.assertEqual(sent_params["q"], payload["q"])
        self.assertEqual(sent_params["categories"], "general,science")
        self.assertEqual(sent_params["engines"], "google,arxiv")
        self.assertEqual(sent_params["language"], "en")
        self.assertEqual(sent_params["time_range"], "month")
        self.assertEqual(sent_params["theme"], "simple")
        self.assertEqual(sent_params["image_proxy"], "1")
        self.assertEqual(response["result_order"], "newest")
        self.assertEqual(response["result_count"], 1)
        self.assertEqual(response["results"][0]["domain"], "example.org")
        self.assertEqual(response["unresponsive_engines"], ["duckduckgo"])

    @override_settings(SEARXNG_BASE_URL="http://searxng:8080", SEARXNG_TIMEOUT_S=5)
    @patch("core.services.SearxNGClient.search")
    def test_run_direct_searxng_search_orders_results_by_newest_first(self, search_mock):
        SearchProviderConfig.load()
        search_mock.return_value = {
            "number_of_results": 3,
            "suggestions": [],
            "answers": [],
            "corrections": [],
            "infoboxes": [],
            "unresponsive_engines": [],
            "results": [
                {
                    "title": "Relevant but older",
                    "url": "https://example.org/older",
                    "content": "Older item",
                    "engine": "google",
                    "score": 0.95,
                    "published_at": "2025-01-01T00:00:00Z",
                },
                {
                    "title": "Newest item",
                    "url": "https://example.org/newest",
                    "content": "Newest item",
                    "engine": "google",
                    "score": 0.2,
                    "published_at": "2025-05-01T00:00:00Z",
                },
            ],
        }

        response = run_direct_searxng_search(
            {
                "q": "open science",
                "result_order": "newest",
                "max_results": 10,
            }
        )

        self.assertEqual([item["title"] for item in response["results"]], ["Newest item", "Relevant but older"])

    @override_settings(SEARXNG_BASE_URL="http://searxng:8080", SEARXNG_TIMEOUT_S=30)
    @patch(
        "core.services.load_searxng_categories",
        return_value=["general", "web", "news", "science", "files"],
    )
    @patch("core.services.SearxNGClient.search")
    def test_run_direct_searxng_search_returns_partial_results_after_batch_timeout(
        self,
        search_mock,
        _categories_mock,
    ):
        SearchProviderConfig.load()
        search_mock.side_effect = [
            httpx.ReadTimeout("timed out"),
            {
                "number_of_results": 1,
                "suggestions": [],
                "answers": [],
                "corrections": [],
                "infoboxes": [],
                "unresponsive_engines": [],
                "results": [
                    {
                        "title": "Recovered result",
                        "url": "https://example.org/recovered",
                        "content": "Recovered after the first batch timed out",
                        "engine": "google",
                        "score": 0.8,
                    }
                ],
            },
        ]

        response = run_direct_searxng_search(
            {
                "q": "david meyer",
                "use_all_categories": True,
                "categories": [],
                "use_all_engines": True,
                "engines": [],
                "max_results": 10,
                "include_domains": [],
                "exclude_domains": [],
            }
        )

        self.assertEqual(search_mock.call_count, 2)
        self.assertEqual(response["result_count"], 1)
        self.assertEqual(response["results"][0]["url"], "https://example.org/recovered")
        self.assertEqual(len(response["warnings"]), 1)
        self.assertEqual(response["request_count"], 2)


class AuthAccessTests(OwnedTestCase):
    def test_dashboard_requires_authentication(self):
        response = self.client.get("/api/v1/dashboard/")

        self.assertEqual(response.status_code, 403)

    @override_settings(
        SOCIAL_LOGIN_PROVIDERS=[
            {
                "id": "google",
                "name": "Google",
                "login_path": "/api/v1/auth/social/google/login/",
            }
        ],
        SOCIAL_AUTH_PUBLIC_BASE_URL="",
    )
    def test_auth_providers_lists_configured_social_providers(self):
        response = self.client.get("/api/v1/auth/providers/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "providers": [
                    {
                        "id": "google",
                        "name": "Google",
                        "login_path": "/api/v1/auth/social/google/login/",
                        "login_url": "http://testserver/api/v1/auth/social/google/login/",
                        "callback_url": "http://testserver/api/v1/auth/social/google/login/callback/",
                    }
                ]
            },
        )

    @override_settings(
        SOCIALACCOUNT_PROVIDERS={
            "google": {
                "APPS": [
                    {
                        "client_id": "google-client-id",
                        "secret": "google-client-secret",
                    }
                ],
                "SCOPE": ["profile", "email"],
                "AUTH_PARAMS": {
                    "access_type": "online",
                    "prompt": "select_account",
                },
            }
        },
        SOCIAL_AUTH_PUBLIC_BASE_URL="https://localhost:8443",
    )
    def test_google_login_uses_configured_public_base_url_for_redirect_uri(self):
        response = self.client.get(
            "/api/v1/auth/social/google/login/?process=login",
            HTTP_HOST="localhost:8077",
        )

        self.assertEqual(response.status_code, 302)
        location = response["Location"]
        params = parse_qs(urlparse(location).query)
        self.assertEqual(
            params["redirect_uri"][0],
            "https://localhost:8443/api/v1/auth/social/google/login/callback/",
        )

    def test_dashboard_and_results_are_scoped_to_authenticated_user(self):
        other_user = get_user_model().objects.create_user(
            username="other-user",
            email="other@example.com",
            password="secret123",
        )
        source = SourceScope.objects.create(
            owner=self.user,
            name="My Research Scope",
            kind=SourceScope.Kind.RESEARCH,
        )
        other_source = SourceScope.objects.create(
            owner=other_user,
            name="Other Research Scope",
            kind=SourceScope.Kind.RESEARCH,
        )
        my_topic = SearchTopic.objects.create(
            owner=self.user,
            name="My Topic",
            queries=["research data exchange"],
        )
        other_topic = SearchTopic.objects.create(
            owner=other_user,
            name="Other Topic",
            queries=["data platform"],
        )
        my_topic.source_scopes.add(source)
        other_topic.source_scopes.add(other_source)
        SearchResult.objects.create(
            topic=my_topic,
            source_scope=source,
            title="My Result",
            url="https://example.org/my-result",
            normalized_url="https://example.org/my-result",
            domain="example.org",
        )
        SearchResult.objects.create(
            topic=other_topic,
            source_scope=other_source,
            title="Other Result",
            url="https://example.org/other-result",
            normalized_url="https://example.org/other-result",
            domain="example.org",
        )

        self.client.force_login(self.user)

        dashboard_response = self.client.get("/api/v1/dashboard/")
        results_response = self.client.get("/api/v1/results/")

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertEqual(results_response.status_code, 200)
        self.assertEqual(dashboard_response.json()["stats"]["topic_count"], 1)
        self.assertEqual(
            [topic["name"] for topic in dashboard_response.json()["topics"]],
            ["My Topic"],
        )
        self.assertEqual(
            [source_scope["name"] for source_scope in dashboard_response.json()["sources"]],
            ["My Research Scope"],
        )
        self.assertEqual(
            [result["title"] for result in results_response.json()["results"]],
            ["My Result"],
        )
