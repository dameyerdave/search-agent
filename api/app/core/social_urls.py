from django.urls import path

from . import social_auth


urlpatterns = [
    path("google/login/", social_auth.google_oauth2_login, name="google_login"),
    path(
        "google/login/callback/",
        social_auth.google_oauth2_callback,
        name="google_callback",
    ),
    path(
        "google/login/token/",
        social_auth.login_by_token,
        name="google_login_by_token",
    ),
    path("github/login/", social_auth.github_oauth2_login, name="github_login"),
    path(
        "github/login/callback/",
        social_auth.github_oauth2_callback,
        name="github_callback",
    ),
    path(
        "microsoft/login/",
        social_auth.microsoft_oauth2_login,
        name="microsoft_login",
    ),
    path(
        "microsoft/login/callback/",
        social_auth.microsoft_oauth2_callback,
        name="microsoft_callback",
    ),
]
