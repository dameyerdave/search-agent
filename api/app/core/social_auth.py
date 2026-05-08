from urllib.parse import urlsplit

from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.google.views import (
    GoogleOAuth2Adapter,
    login_by_token,
)
from allauth.socialaccount.providers.microsoft.views import (
    MicrosoftGraphOAuth2Adapter,
)
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2CallbackView,
    OAuth2LoginView,
)
from django.conf import settings
from django.urls import reverse


def social_auth_public_base_url() -> str:
    return getattr(settings, "SOCIAL_AUTH_PUBLIC_BASE_URL", "").rstrip("/")


class PublicBaseOAuth2AdapterMixin:
    def get_callback_url(self, request, app):
        public_base_url = social_auth_public_base_url()
        if public_base_url:
            return f"{public_base_url}{reverse(f'{self.provider_id}_callback')}"
        return super().get_callback_url(request, app)


class SearchAgentOAuth2LoginView(OAuth2LoginView):
    def get_provider(self):
        provider = self.adapter.get_provider()
        provider.oauth2_adapter_class = self.adapter.__class__
        return provider


class SearchAgentGoogleOAuth2Adapter(
    PublicBaseOAuth2AdapterMixin, GoogleOAuth2Adapter
):
    pass


class SearchAgentGitHubOAuth2Adapter(
    PublicBaseOAuth2AdapterMixin, GitHubOAuth2Adapter
):
    pass


class SearchAgentMicrosoftOAuth2Adapter(
    PublicBaseOAuth2AdapterMixin, MicrosoftGraphOAuth2Adapter
):
    pass


google_oauth2_login = SearchAgentOAuth2LoginView.adapter_view(
    SearchAgentGoogleOAuth2Adapter
)
google_oauth2_callback = OAuth2CallbackView.adapter_view(SearchAgentGoogleOAuth2Adapter)

github_oauth2_login = SearchAgentOAuth2LoginView.adapter_view(
    SearchAgentGitHubOAuth2Adapter
)
github_oauth2_callback = OAuth2CallbackView.adapter_view(SearchAgentGitHubOAuth2Adapter)

microsoft_oauth2_login = SearchAgentOAuth2LoginView.adapter_view(
    SearchAgentMicrosoftOAuth2Adapter
)
microsoft_oauth2_callback = OAuth2CallbackView.adapter_view(
    SearchAgentMicrosoftOAuth2Adapter
)


def build_social_provider_payload(provider_id: str, name: str, request) -> dict:
    login_path = reverse(f"{provider_id}_login")
    callback_path = reverse(f"{provider_id}_callback")
    public_base_url = social_auth_public_base_url()
    if public_base_url:
        login_url = f"{public_base_url}{login_path}"
        callback_url = f"{public_base_url}{callback_path}"
    else:
        login_url = request.build_absolute_uri(login_path)
        callback_url = request.build_absolute_uri(callback_path)
    return {
        "id": provider_id,
        "name": name,
        "login_path": login_path,
        "login_url": login_url,
        "callback_url": callback_url,
    }
