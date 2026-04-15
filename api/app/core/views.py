from django.db.models import Count, Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_GET
import httpx
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import SearchProviderConfig, SearchResult, SearchRun, SearchTopic, SourceScope
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
def dashboard(_request):
    provider = SearchProviderConfig.load()
    topics = (
        SearchTopic.objects.prefetch_related("source_scopes")
        .annotate(
            result_count=Count("results", distinct=True),
            new_results_count=Count(
                "results",
                filter=Q(results__is_new=True),
                distinct=True,
            ),
        )
        .order_by("name")
    )
    results = (
        SearchResult.objects.select_related("topic", "source_scope", "last_run")
        .order_by("-is_new", "-published_at", "-first_seen_at")[:10]
    )
    runs = SearchRun.objects.select_related("topic").order_by("-started_at")[:10]
    sources = SourceScope.objects.order_by("sort_order", "name")

    payload = {
        "provider": SearchProviderConfigSerializer(provider).data,
        "stats": {
            "topic_count": SearchTopic.objects.count(),
            "enabled_topic_count": SearchTopic.objects.filter(enabled=True).count(),
            "source_count": SourceScope.objects.count(),
            "result_count": SearchResult.objects.count(),
            "new_result_count": SearchResult.objects.filter(is_new=True).count(),
            "run_count": SearchRun.objects.count(),
            "successful_run_count": SearchRun.objects.filter(
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
@permission_classes([AllowAny])
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
