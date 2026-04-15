from django.db.models import Count, Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import SearchProviderConfig, SearchResult, SearchRun, SearchTopic, SourceScope
from .serializers import (
    SearchProviderConfigSerializer,
    SearchResultSerializer,
    SearchRunSerializer,
    SearchTopicSerializer,
    SourceScopeSerializer,
)
from .services import run_topic_search


def topic_queryset():
    return SearchTopic.objects.prefetch_related("source_scopes").annotate(
        result_count=Count("results", distinct=True),
        new_results_count=Count(
            "results",
            filter=Q(results__is_new=True),
            distinct=True,
        ),
    )


class SourceScopeViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = SourceScope.objects.all()
    serializer_class = SourceScopeSerializer


class SearchTopicViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = topic_queryset()
    serializer_class = SearchTopicSerializer
    lookup_field = "slug"

    @action(detail=True, methods=["post"])
    def run_now(self, request, slug=None):
        topic = SearchTopic.objects.get(slug=slug)
        run = run_topic_search(topic)
        serializer = SearchRunSerializer(run)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, slug=None):
        topic = SearchTopic.objects.get(slug=slug)
        updated = topic.results.filter(is_new=True).update(is_new=False)
        return Response({"acknowledged": updated})


class SearchProviderConfigViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = SearchProviderConfig.objects.all()
    serializer_class = SearchProviderConfigSerializer
    http_method_names = ["get", "patch", "put", "head", "options"]

    def get_queryset(self):
        SearchProviderConfig.load()
        return super().get_queryset()


class SearchRunViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = SearchRun.objects.select_related("topic").all()
    serializer_class = SearchRunSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        topic = self.request.query_params.get("topic")
        status_value = self.request.query_params.get("status")
        if topic:
            queryset = queryset.filter(topic__slug=topic)
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset


class SearchResultViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = SearchResult.objects.select_related("topic", "source_scope", "last_run").all()
    serializer_class = SearchResultSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        topic = self.request.query_params.get("topic")
        scope = self.request.query_params.get("scope")
        kind = self.request.query_params.get("kind")
        only_new = self.request.query_params.get("is_new")
        query = self.request.query_params.get("q")

        if topic:
            queryset = queryset.filter(topic__slug=topic)
        if scope:
            queryset = queryset.filter(source_scope_id=scope)
        if kind:
            queryset = queryset.filter(source_scope__kind=kind)
        if only_new in {"true", "false"}:
            queryset = queryset.filter(is_new=only_new == "true")
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(snippet__icontains=query)
                | Q(content__icontains=query)
                | Q(url__icontains=query)
                | Q(domain__icontains=query)
            )
        return queryset

    @action(detail=False, methods=["post"])
    def acknowledge(self, request):
        ids = request.data.get("ids") or []
        topic_slug = request.data.get("topic")
        queryset = SearchResult.objects.filter(is_new=True)
        if ids:
            queryset = queryset.filter(id__in=ids)
        if topic_slug:
            queryset = queryset.filter(topic__slug=topic_slug)
        updated = queryset.update(is_new=False)
        return Response({"acknowledged": updated})
