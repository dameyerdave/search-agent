from datetime import timedelta
from unittest.mock import patch

import httpx
from django.test import TestCase
from django.test import override_settings
from django.utils import timezone

from .models import SearchProviderConfig, SearchTopic, SourceScope
from .services import (
    build_direct_searxng_params,
    build_search_query,
    build_searxng_params,
    run_direct_searxng_search,
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


class ModelDefaultsTests(TestCase):
    def test_provider_config_load_creates_default_singleton(self):
        config = SearchProviderConfig.load()

        self.assertEqual(config.name, "searxng")
        self.assertTrue(config.enabled)

    def test_topic_slug_is_generated(self):
        topic = SearchTopic.objects.create(
            name="Research Data Exchange Landscape",
            queries=["research data exchange"],
        )
        self.assertEqual(topic.slug, "research-data-exchange-landscape")
        self.assertEqual(topic.schedule_every, 1)
        self.assertEqual(topic.schedule_unit, SearchTopic.ScheduleUnit.DAYS)
        self.assertIsNotNone(topic.next_run_at)

    def test_topic_can_link_to_sources(self):
        source = SourceScope.objects.create(name="Research", kind=SourceScope.Kind.RESEARCH)
        topic = SearchTopic.objects.create(name="Data Platforms", queries=["data platform"])
        topic.source_scopes.add(source)

        self.assertEqual(topic.source_scopes.count(), 1)

    def test_source_scope_supports_searxng_categories(self):
        source = SourceScope.objects.create(
            name="Public",
            kind=SourceScope.Kind.PUBLIC,
            searxng_categories=["general", "news"],
            time_range=SourceScope.TimeRange.AUTO,
        )

        self.assertEqual(source.searxng_categories, ["general", "news"])
        self.assertTrue(source.use_all_categories)
        self.assertTrue(source.use_all_engines)

    def test_topic_schedule_updates_next_run_when_changed(self):
        topic = SearchTopic.objects.create(
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
            name="Paused Topic",
            queries=["data platform"],
        )

        topic.enabled = False
        topic.save()
        topic.refresh_from_db()

        self.assertIsNone(topic.next_run_at)


class SchedulerTaskTests(TestCase):
    @patch("core.tasks.run_topic_search_task.delay")
    def test_dispatch_due_topic_searches_queues_only_due_topics(self, delay_mock):
        due_topic = SearchTopic.objects.create(
            name="Due Topic",
            queries=["research data exchange"],
            schedule_every=15,
            schedule_unit=SearchTopic.ScheduleUnit.MINUTES,
        )
        future_topic = SearchTopic.objects.create(
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


class DirectSearxNGSearchTests(TestCase):
    @patch("core.services.load_searxng_categories", return_value=["general", "science", "news"])
    def test_build_searxng_params_uses_all_categories_by_default(self, _categories_mock):
        topic = SearchTopic.objects.create(
            name="All Categories Topic",
            queries=["research data exchange"],
        )
        source = SourceScope.objects.create(
            name="All Categories Scope",
            kind=SourceScope.Kind.PUBLIC,
            searxng_categories=["general"],
            use_all_categories=True,
        )

        params = build_searxng_params(topic, source, '"research data exchange"')

        self.assertEqual(params["categories"], "general,science,news")

    def test_build_searxng_params_can_restrict_categories_when_requested(self):
        topic = SearchTopic.objects.create(
            name="Restricted Categories Topic",
            queries=["research data exchange"],
        )
        source = SourceScope.objects.create(
            name="Restricted Categories Scope",
            kind=SourceScope.Kind.PUBLIC,
            searxng_categories=["science", "files"],
            use_all_categories=False,
        )

        params = build_searxng_params(topic, source, '"research data exchange"')

        self.assertEqual(params["categories"], "science,files")

    def test_build_searxng_params_uses_all_engines_by_default(self):
        topic = SearchTopic.objects.create(
            name="All Engines Topic",
            queries=["research data exchange"],
        )
        source = SourceScope.objects.create(
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
            name="Restricted Engines Topic",
            queries=["research data exchange"],
        )
        source = SourceScope.objects.create(
            name="Restricted Engines Scope",
            kind=SourceScope.Kind.PUBLIC,
            searxng_engines=["google", "arxiv"],
            use_all_engines=False,
        )

        params = build_searxng_params(topic, source, '"research data exchange"')

        self.assertEqual(params["engines"], "google,arxiv")

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

    @override_settings(SEARXNG_BASE_URL="http://searxng:8080", SEARXNG_TIMEOUT_S=5)
    @patch("core.services.SearxNGClient.search")
    def test_run_direct_searxng_search_filters_domains_and_keeps_extra_params(self, search_mock):
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
        self.assertEqual(sent_params["language"], "en-US")
        self.assertEqual(sent_params["time_range"], "month")
        self.assertEqual(sent_params["theme"], "simple")
        self.assertEqual(sent_params["image_proxy"], "1")
        self.assertEqual(response["result_count"], 1)
        self.assertEqual(response["results"][0]["domain"], "example.org")
        self.assertEqual(response["unresponsive_engines"], ["duckduckgo"])

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
