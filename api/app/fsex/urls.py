from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from rest_framework import permissions
from rest_framework.routers import DefaultRouter

from core import views
from core.viewsets import (
    PushSubscriptionViewSet,
    SavedFolderViewSet,
    SearchProviderConfigViewSet,
    SearchResultViewSet,
    SearchRunViewSet,
    SearchTopicViewSet,
    SourceScopeViewSet,
)

router = DefaultRouter()
router.register("source-scopes", SourceScopeViewSet, basename="source-scope")
router.register("topics", SearchTopicViewSet, basename="topic")
router.register("provider-config", SearchProviderConfigViewSet, basename="provider-config")
router.register("runs", SearchRunViewSet, basename="run")
router.register("results", SearchResultViewSet, basename="result")
router.register("folders", SavedFolderViewSet, basename="folder")
router.register("push-subscriptions", PushSubscriptionViewSet, basename="push-subscription")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", views.health, name="health"),
    path("api/v1/auth/csrf/", views.csrf, name="csrf"),
    path("api/v1/auth/user/", views.auth_user, name="auth-user"),
    path("api/v1/auth/logout/", views.auth_logout, name="auth-logout"),
    path("api/v1/dashboard/", views.dashboard, name="dashboard"),
    path("api/v1/searxng/search/", views.searxng_search, name="searxng-search"),
    path("api/v1/", include(router.urls)),
]

if settings.DEBUG:
    from drf_spectacular.views import (
        SpectacularAPIView,
        SpectacularRedocView,
        SpectacularSwaggerView,
    )

    urlpatterns += [
        # OpenAPI 3 schema
        path(
            "api/v1/schema/",
            SpectacularAPIView.as_view(
                permission_classes=[permissions.AllowAny],
                authentication_classes=[],
            ),
            name="schema",
        ),
        # Swagger UI
        path(
            "api/v1/schema/swagger-ui/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="schema-swagger-ui",
        ),
        # ReDoc UI (optional)
        path(
            "api/v1/schema/redoc/",
            SpectacularRedocView.as_view(url_name="schema"),
            name="schema-redoc",
        ),
    ]
