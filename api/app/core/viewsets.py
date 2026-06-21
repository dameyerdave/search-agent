from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .map_serializers import SearchResultMapResponseSerializer
from .models import SavedFolder, SearchProviderConfig, SearchResult, SearchRun, SearchTopic, SourceScope
from .querysets import owned_folders, owned_results, owned_runs, owned_source_scopes, owned_topics
from .tasks import run_topic_search_task
from .result_locations import build_result_location_map_payload
from .serializers import (
    SavedFolderSerializer,
    SearchProviderConfigSerializer,
    SearchResultSerializer,
    SearchRunSerializer,
    SearchTopicSerializer,
    SourceScopeSerializer,
)
from .services import normalize_url, run_topic_search


def _resolve_folder(request, user):
    """Return a SavedFolder (or None) from folder_id or folder_name in request.data."""
    folder_id = request.data.get("folder_id")
    folder_name = (request.data.get("folder_name") or "").strip()
    if folder_id:
        try:
            return SavedFolder.objects.get(pk=folder_id, owner=user)
        except SavedFolder.DoesNotExist:
            return None
    if folder_name:
        folder, _ = SavedFolder.objects.get_or_create(
            owner=user, name=folder_name, defaults={"sort_order": 0}
        )
        return folder
    return None


class SourceScopeViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = SourceScope.objects.none()
    serializer_class = SourceScopeSerializer

    def get_queryset(self):
        return owned_source_scopes(self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class SearchTopicViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = SearchTopic.objects.none()
    serializer_class = SearchTopicSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return owned_topics(self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"])
    def run_now(self, request, slug=None):
        topic = self.get_object()
        run = SearchRun.objects.create(
            topic=topic,
            status=SearchRun.Status.RUNNING,
            source_scope_count=0,
            query_snapshot=[],
        )
        topic.last_run_status = SearchTopic.RunStatus.RUNNING
        topic.last_checked_at = timezone.now()
        topic.save(update_fields=["last_run_status", "last_checked_at", "updated_at"])
        run_topic_search_task.delay(topic.pk, run.pk)
        serializer = SearchRunSerializer(run)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, slug=None):
        topic = self.get_object()
        updated = topic.results.filter(is_new=True).update(is_new=False)
        return Response({"acknowledged": updated})


class SearchProviderConfigViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = SearchProviderConfig.objects.all()
    serializer_class = SearchProviderConfigSerializer
    http_method_names = ["get", "patch", "put", "head", "options"]

    def get_queryset(self):
        SearchProviderConfig.load()
        return super().get_queryset()


class SearchRunViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = SearchRun.objects.none()
    serializer_class = SearchRunSerializer

    def get_queryset(self):
        queryset = owned_runs(self.request.user)
        topic = self.request.query_params.get("topic")
        status_value = self.request.query_params.get("status")
        if topic:
            queryset = queryset.filter(topic__slug=topic)
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset


class SearchResultViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = SearchResult.objects.none()
    serializer_class = SearchResultSerializer

    def get_queryset(self):
        queryset = owned_results(self.request.user)
        topic = self.request.query_params.get("topic")
        scope = self.request.query_params.get("scope")
        kind = self.request.query_params.get("kind")
        only_new = self.request.query_params.get("is_new")
        only_saved = self.request.query_params.get("is_saved")
        folder_param = self.request.query_params.get("folder")
        query = self.request.query_params.get("q")

        if topic:
            queryset = queryset.filter(topic__slug=topic)
        if scope:
            queryset = queryset.filter(source_scope_id=scope)
        if kind:
            queryset = queryset.filter(source_scope__kind=kind)
        if only_new in {"true", "false"}:
            queryset = queryset.filter(is_new=only_new == "true")
        if only_saved in {"true", "false"}:
            queryset = queryset.filter(is_saved=only_saved == "true")
        if folder_param == "unfiled":
            queryset = queryset.filter(is_saved=True, folder__isnull=True)
        elif folder_param:
            queryset = queryset.filter(folder_id=folder_param)
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(snippet__icontains=query)
                | Q(content__icontains=query)
                | Q(url__icontains=query)
                | Q(domain__icontains=query)
            )
        return queryset

    @action(detail=False, methods=["get"], url_path="map")
    def map(self, _request):
        payload = build_result_location_map_payload(self.get_queryset())
        serializer = SearchResultMapResponseSerializer(payload)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def acknowledge(self, request):
        ids = request.data.get("ids") or []
        topic_slug = request.data.get("topic")
        queryset = owned_results(request.user).filter(is_new=True)
        if ids:
            queryset = queryset.filter(id__in=ids)
        if topic_slug:
            queryset = queryset.filter(topic__slug=topic_slug)
        updated = queryset.update(is_new=False)
        return Response({"acknowledged": updated})

    @action(detail=True, methods=["post"])
    def save(self, request, pk=None):
        result = self.get_object()
        title = (request.data.get("title") or "").strip() or result.title
        folder = _resolve_folder(request, request.user)
        result.is_saved = True
        result.saved_title = title
        result.folder = folder
        result.save(update_fields=["is_saved", "saved_title", "folder", "updated_at"])
        return Response(SearchResultSerializer(result, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def unsave(self, request, pk=None):
        result = self.get_object()
        result.is_saved = False
        result.saved_title = ""
        result.folder = None
        result.save(update_fields=["is_saved", "saved_title", "folder", "updated_at"])
        return Response(SearchResultSerializer(result, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def move(self, request, pk=None):
        result = self.get_object()
        folder = _resolve_folder(request, request.user)
        result.folder = folder
        result.save(update_fields=["folder", "updated_at"])
        return Response(SearchResultSerializer(result, context={"request": request}).data)

    @action(detail=False, methods=["post"], url_path="save_live")
    def save_live(self, request):
        url = (request.data.get("url") or "").strip()
        if not url:
            return Response({"error": "url required"}, status=status.HTTP_400_BAD_REQUEST)
        title = (request.data.get("title") or "").strip() or url
        domain = (request.data.get("domain") or "").strip()
        snippet = (request.data.get("snippet") or "").strip()
        folder = _resolve_folder(request, request.user)
        normed = normalize_url(url)
        result, _ = SearchResult.objects.get_or_create(
            owner=request.user,
            normalized_url=normed,
            topic=None,
            defaults={
                "title": title,
                "url": url,
                "domain": domain,
                "snippet": snippet,
                "is_saved": True,
                "saved_title": title,
                "folder": folder,
                "is_new": False,
            },
        )
        if not result.is_saved:
            result.is_saved = True
            result.saved_title = title
            result.folder = folder
            result.save(update_fields=["is_saved", "saved_title", "folder", "updated_at"])
        return Response(SearchResultSerializer(result, context={"request": request}).data)


class SavedFolderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = SavedFolder.objects.none()
    serializer_class = SavedFolderSerializer

    def get_queryset(self):
        return owned_folders(self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
