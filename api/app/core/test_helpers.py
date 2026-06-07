from unittest.mock import patch


class MockCloudflareAccessTokenVerifier:
    def __init__(self, claims_by_token):
        self.claims_by_token = claims_by_token

    def verify(self, token):
        if token not in self.claims_by_token:
            raise AssertionError(f"Unexpected Cloudflare Access test token: {token}")
        return self.claims_by_token[token]


class CloudflareAccessTestMixin:
    def setUp(self):
        super().setUp()
        self._cloudflare_claims_by_token = {}
        self._cloudflare_verifier = MockCloudflareAccessTokenVerifier(
            self._cloudflare_claims_by_token
        )
        self._cloudflare_verifier_patcher = patch(
            "core.authentication.get_cloudflare_access_token_verifier",
            return_value=self._cloudflare_verifier,
        )
        self._cloudflare_verifier_patcher.start()
        self.addCleanup(self._cloudflare_verifier_patcher.stop)

    def set_cloudflare_identity(
        self,
        *,
        user=None,
        token="cloudflare-test-token",
        subject=None,
        email=None,
        first_name="Test",
        last_name="User",
    ):
        if user is not None:
            email = email or user.email
            subject = subject or f"cloudflare-{user.pk}"
            first_name = first_name if first_name != "Test" else user.first_name or "Test"
            last_name = last_name if last_name != "User" else user.last_name or "User"

        self._cloudflare_claims_by_token[token] = {
            "sub": subject or f"cloudflare-{token}",
            "email": email or "",
            "given_name": first_name,
            "family_name": last_name,
            "iss": "https://search-agent.cloudflareaccess.com",
            "aud": ["search-agent-test-audience"],
        }
        self.client.defaults["HTTP_CF_ACCESS_JWT_ASSERTION"] = token
        return token
