from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import SearchTopic, SourceScope


class SearchTopicApiTests(TestCase):
    def setUp(self):
        super().setUp()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="topic-api-user",
            email="topic-api-user@example.com",
            password="secret123",
        )
        self.other_user = user_model.objects.create_user(
            username="topic-api-other-user",
            email="topic-api-other-user@example.com",
            password="secret123",
        )

    def topic_payload(self, source_scope_ids):
        return {
            "name": "Ukraine Watch",
            "description": "Track Ukraine news.",
            "enabled": True,
            "queries": ["ukraine krieg"],
            "required_terms": [],
            "excluded_terms": [],
            "lookback_days": 30,
            "schedule_every": 1,
            "schedule_unit": "days",
            "max_results_per_query": 10,
            "notes": "Saved from tests.",
            "source_scope_ids": source_scope_ids,
        }

    def test_create_topic_accepts_owned_source_scope_ids(self):
        source = SourceScope.objects.create(
            owner=self.user,
            name="Live Search Scope",
            kind=SourceScope.Kind.CUSTOM,
        )

        self.client.force_login(self.user)
        response = self.client.post(
            "/api/v1/topics/",
            self.topic_payload([source.id]),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        topic = SearchTopic.objects.get(owner=self.user, name="Ukraine Watch")
        self.assertEqual(list(topic.source_scopes.values_list("id", flat=True)), [source.id])

    def test_create_topic_rejects_other_users_source_scope_ids(self):
        source = SourceScope.objects.create(
            owner=self.other_user,
            name="Other User Scope",
            kind=SourceScope.Kind.CUSTOM,
        )

        self.client.force_login(self.user)
        response = self.client.post(
            "/api/v1/topics/",
            self.topic_payload([source.id]),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("source_scope_ids", response.json())
