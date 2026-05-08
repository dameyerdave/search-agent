from django.conf import settings
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_GET
import httpx
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import SearchProviderConfig, SearchRun
from .querysets import owned_results, owned_runs, owned_source_scopes, owned_topics
from .social_auth import build_social_provider_payload
from .serializers import (
    SearxNGSearchRequestSerializer,
    SearchProviderConfigSerializer,
    SearchResultSerializer,
    SearchRunSerializer,
    SearchTopicSerializer,
    SourceScopeSerializer,
)
from .services import run_direct_searxng_search


def health(_request):
    return JsonResponse({"status": "ok", "service": "search-agent-api"})


@require_GET
def csrf(request):
    token = get_token(request)
    response = JsonResponse({"csrfToken": token})
    response["X-CSRFToken"] = token
    return response


@api_view(["GET"])
@permission_classes([AllowAny])
def auth_providers(request):
    providers = [
        build_social_provider_payload(provider["id"], provider["name"], request)
        for provider in getattr(settings, "SOCIAL_LOGIN_PROVIDERS", [])
    ]
    return Response({"providers": providers})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    provider = SearchProviderConfig.load()
    user = request.user
    topics = owned_topics(user).order_by("name")
    results = owned_results(user).order_by("-is_new", "-published_at", "-first_seen_at")[:10]
    runs = owned_runs(user).order_by("-started_at")[:10]
    sources = owned_source_scopes(user).order_by("sort_order", "name")

    payload = {
        "provider": SearchProviderConfigSerializer(provider).data,
        "stats": {
            "topic_count": topics.count(),
            "enabled_topic_count": topics.filter(enabled=True).count(),
            "source_count": sources.count(),
            "result_count": owned_results(user).count(),
            "new_result_count": owned_results(user).filter(is_new=True).count(),
            "run_count": owned_runs(user).count(),
            "successful_run_count": owned_runs(user).filter(
                status=SearchRun.Status.SUCCEEDED
            ).count(),
        },
        "topics": SearchTopicSerializer(topics, many=True).data,
        "sources": SourceScopeSerializer(sources, many=True).data,
        "recent_results": SearchResultSerializer(results, many=True).data,
        "recent_runs": SearchRunSerializer(runs, many=True).data,
    }
    return Response(payload)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def searxng_search(request):
    serializer = SearxNGSearchRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        payload = run_direct_searxng_search(serializer.validated_data)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=400)
    except httpx.ReadTimeout as exc:
        return Response({"detail": f"SearxNG request timed out: {exc}"}, status=504)
    except httpx.HTTPError as exc:
        return Response({"detail": f"SearxNG request failed: {exc}"}, status=502)

    return Response(payload)
