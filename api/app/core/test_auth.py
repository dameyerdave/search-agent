import json
from django.contrib.auth import get_user_model
from django.test import TestCase
from unittest.mock import Mock, patch

import jwt
from rest_framework import exceptions

from .authentication import CloudflareAccessTokenVerifier
from .models import CloudflareAccessIdentity, SearchResult, SearchTopic, SourceScope
from .test_helpers import CloudflareAccessTestMixin


class CloudflareAccessAuthTests(CloudflareAccessTestMixin, TestCase):
    def test_dashboard_requires_cloudflare_identity(self):
        response = self.client.get("/api/v1/dashboard/")

        self.assertEqual(response.status_code, 403)

    def test_auth_user_requires_cloudflare_identity(self):
        response = self.client.get("/api/v1/auth/user/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "authenticated": False,
                "user": None,
            },
        )

    def test_auth_user_creates_a_user_from_cloudflare_claims(self):
        self.set_cloudflare_identity(
            token="new-user-token",
            subject="subject-123",
            email="ada@example.com",
            first_name="Ada",
            last_name="Lovelace",
        )

        response = self.client.get("/api/v1/auth/user/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["authenticated"])
        self.assertEqual(payload["user"]["email"], "ada@example.com")
        self.assertEqual(payload["user"]["first_name"], "Ada")
        self.assertEqual(payload["user"]["last_name"], "Lovelace")

        user = get_user_model().objects.get(email="ada@example.com")
        identity = CloudflareAccessIdentity.objects.get(subject="subject-123")
        self.assertEqual(identity.user, user)

    def test_auth_user_reuses_existing_user_by_email(self):
        user = get_user_model().objects.create_user(
            username="existing-user",
            email="existing@example.com",
            first_name="Grace",
            last_name="Hopper",
            password="secret123",
        )
        self.set_cloudflare_identity(
            token="existing-user-token",
            subject="existing-subject",
            email="existing@example.com",
            first_name="Grace",
            last_name="Hopper",
        )

        response = self.client.get("/api/v1/auth/user/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["pk"], user.pk)
        identity = CloudflareAccessIdentity.objects.get(subject="existing-subject")
        self.assertEqual(identity.user, user)

    @patch("core.views.run_direct_searxng_search")
    def test_live_search_is_available_without_cloudflare_identity(self, search_mock):
        search_mock.return_value = {
            "query": "metadata exchange",
            "params": {"q": "metadata exchange"},
            "result_order": "relevance",
            "result_count": 1,
            "number_of_results": 1,
            "suggestions": [],
            "answers": [],
            "corrections": [],
            "infoboxes": [],
            "unresponsive_engines": [],
            "results": [
                {
                    "position": 1,
                    "title": "Example result",
                    "url": "https://example.org/result",
                    "domain": "example.org",
                    "snippet": "A result from the public live search endpoint.",
                    "engine": "google",
                    "engines": ["google"],
                    "published_at": None,
                    "score": 0.9,
                    "category": "general",
                    "thumbnail": "",
                    "raw_result": {},
                }
            ],
        }

        response = self.client.post(
            "/api/v1/searxng/search/",
            {"q": "metadata exchange"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result_count"], 1)
        search_mock.assert_called_once()

    def test_dashboard_and_results_are_scoped_to_authenticated_user(self):
        user = get_user_model().objects.create_user(
            username="cloudflare-user",
            email="cloudflare-user@example.com",
            password="secret123",
        )
        other_user = get_user_model().objects.create_user(
            username="other-user",
            email="other@example.com",
            password="secret123",
        )
        source = SourceScope.objects.create(
            owner=user,
            name="My Research Scope",
            kind=SourceScope.Kind.RESEARCH,
        )
        other_source = SourceScope.objects.create(
            owner=other_user,
            name="Other Research Scope",
            kind=SourceScope.Kind.RESEARCH,
        )
        my_topic = SearchTopic.objects.create(
            owner=user,
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
        self.set_cloudflare_identity(
            token="scoped-user-token",
            subject="scoped-user-subject",
            email=user.email,
        )

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


class CloudflareAccessTokenVerifierTests(TestCase):
    @patch("core.authentication.jwt.decode")
    @patch.object(CloudflareAccessTokenVerifier, "_get_signing_key")
    @patch("core.authentication.jwt.get_unverified_header")
    def test_verify_accepts_issuer_with_trailing_slash(
        self,
        get_unverified_header,
        get_signing_key,
        decode,
    ):
        get_unverified_header.return_value = {"kid": "kid-1"}
        get_signing_key.return_value = object()
        decode.return_value = {
            "iss": "https://xuno-search-agent.cloudflareaccess.com/",
            "aud": ["test-audience"],
        }
        verifier = CloudflareAccessTokenVerifier(
            team_domain="https://xuno-search-agent.cloudflareaccess.com",
            audience="test-audience",
            jwks_cache_ttl_s=300,
        )

        claims = verifier.verify("cloudflare-token")

        self.assertEqual(claims["iss"], "https://xuno-search-agent.cloudflareaccess.com/")
        decode.assert_called_once()

    @patch("core.authentication.jwt.decode")
    @patch.object(CloudflareAccessTokenVerifier, "_get_signing_key")
    @patch("core.authentication.jwt.get_unverified_header")
    def test_verify_rejects_invalid_audience_with_clear_message(
        self,
        get_unverified_header,
        get_signing_key,
        decode,
    ):
        get_unverified_header.return_value = {"kid": "kid-1"}
        get_signing_key.return_value = object()
        decode.side_effect = jwt.InvalidAudienceError("Audience doesn't match")
        verifier = CloudflareAccessTokenVerifier(
            team_domain="https://xuno-search-agent.cloudflareaccess.com",
            audience="test-audience",
            jwks_cache_ttl_s=300,
        )

        with self.assertRaisesMessage(
            exceptions.AuthenticationFailed,
            "Cloudflare Access token audience did not match the configured audience.",
        ):
            verifier.verify("cloudflare-token")

    @patch("core.authentication.jwt.decode")
    @patch.object(CloudflareAccessTokenVerifier, "_get_signing_key")
    @patch("core.authentication.jwt.get_unverified_header")
    def test_verify_rejects_mismatched_issuer_with_clear_message(
        self,
        get_unverified_header,
        get_signing_key,
        decode,
    ):
        get_unverified_header.return_value = {"kid": "kid-1"}
        get_signing_key.return_value = object()
        decode.return_value = {
            "iss": "https://wrong-team.cloudflareaccess.com",
            "aud": ["test-audience"],
        }
        verifier = CloudflareAccessTokenVerifier(
            team_domain="https://xuno-search-agent.cloudflareaccess.com",
            audience="test-audience",
            jwks_cache_ttl_s=300,
        )

        with self.assertRaisesMessage(
            exceptions.AuthenticationFailed,
            "Cloudflare Access token issuer did not match the configured team domain.",
        ):
            verifier.verify("cloudflare-token")

    @patch("core.authentication.cache")
    @patch("core.authentication.jwt.algorithms.RSAAlgorithm.from_jwk")
    @patch("core.authentication.httpx.get")
    def test_verifier_caches_serializable_jwk_dicts(self, httpx_get, from_jwk, cache_mock):
        key_dict = {
            "kid": "kid-1",
            "kty": "RSA",
            "alg": "RS256",
            "use": "sig",
            "e": "AQAB",
            "n": "test-modulus",
        }
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"keys": [key_dict]}
        httpx_get.return_value = response
        cache_mock.get.return_value = None
        from_jwk.return_value = object()
        verifier = CloudflareAccessTokenVerifier(
            team_domain="https://xuno-search-agent.cloudflareaccess.com",
            audience="test-audience",
            jwks_cache_ttl_s=300,
        )

        signing_key = verifier._get_signing_key("kid-1")

        self.assertIs(signing_key, from_jwk.return_value)
        cache_mock.set.assert_called_once_with(
            verifier.cache_key,
            {"kid-1": key_dict},
            timeout=300,
        )
        from_jwk.assert_called_once_with(json.dumps(key_dict))

    @patch("core.authentication.cache")
    @patch("core.authentication.jwt.algorithms.RSAAlgorithm.from_jwk")
    @patch("core.authentication.httpx.get")
    def test_verifier_rebuilds_signing_keys_from_cached_jwk_dicts(
        self,
        httpx_get,
        from_jwk,
        cache_mock,
    ):
        key_dict = {
            "kid": "kid-1",
            "kty": "RSA",
            "alg": "RS256",
            "use": "sig",
            "e": "AQAB",
            "n": "cached-modulus",
        }
        cache_mock.get.return_value = {"kid-1": key_dict}
        from_jwk.return_value = object()
        verifier = CloudflareAccessTokenVerifier(
            team_domain="https://xuno-search-agent.cloudflareaccess.com",
            audience="test-audience",
            jwks_cache_ttl_s=300,
        )

        signing_key = verifier._get_signing_key("kid-1")

        self.assertIs(signing_key, from_jwk.return_value)
        httpx_get.assert_not_called()
        from_jwk.assert_called_once_with(json.dumps(key_dict))
