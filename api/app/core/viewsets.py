from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .ai_client import AIUnavailable
from .map_serializers import SearchResultMapResponseSerializer
from .models import PushSubscription, SavedFolder, SearchProviderConfig, SearchResult, SearchRun, SearchTopic, SourceScope
from .querysets import owned_folders, owned_results, owned_runs, owned_source_scopes, owned_topics
from .tasks import run_topic_search_task
from .result_locations import build_result_location_map_payload
from .timeline import TimelineUnavailable, generate_topic_timeline
from .timeline_serializers import TopicTimelineSummarySerializer
from .topic_extraction import derive_topic_from_result, suggest_topic_from_text
from .serializers import (
    PushSubscriptionSerializer,
    SavedFolderSerializer,
    SearchProviderConfigSerializer,
    SearchResultSerializer,
    SearchRunSerializer,
    SearchTopicSerializer,
    SourceScopeSerializer,
)
from .services import normalize_url, run_topic_search

PRESS_REVIEW_WINDOW_DAYS = 3


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

    @action(detail=True, methods=["get", "post"])
    def timeline(self, request, slug=None):
        topic = self.get_object()
        if request.method == "POST":
            try:
                summary = generate_topic_timeline(topic)
            except TimelineUnavailable as exc:
                return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        else:
            summary = getattr(topic, "timeline_summary", None)
            if summary is None:
                return Response(None)
        return Response(TopicTimelineSummarySerializer(summary).data)

    @action(detail=False, methods=["post"], url_path="suggest_categories")
    def suggest_categories(self, request):
        description = (request.data.get("description") or "").strip()
        queries = request.data.get("queries") or []
        text = "\n".join([description, *[str(q) for q in queries if str(q).strip()]]).strip()
        if not text:
            return Response(
                {"error": "Provide a description or at least one query to suggest categories from."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            suggestion = suggest_topic_from_text(text)
        except AIUnavailable as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(suggestion)


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
        press_review = request.data.get("press_review")
        queryset = owned_results(request.user).filter(is_new=True)
        if ids:
            queryset = queryset.filter(id__in=ids)
        if topic_slug:
            queryset = queryset.filter(topic__slug=topic_slug)
        if press_review:
            queryset = queryset.filter(topic__include_in_press_review=True)
        updated = queryset.update(is_new=False)
        return Response({"acknowledged": updated})

    @action(detail=False, methods=["get"], url_path="press_review")
    def press_review(self, request):
        window_start = timezone.now() - timedelta(days=PRESS_REVIEW_WINDOW_DAYS)
        queryset = (
            owned_results(request.user)
            .filter(topic__include_in_press_review=True, first_seen_at__gte=window_start)
            .order_by("-first_seen_at")
        )
        page = self.paginate_queryset(queryset)
        serializer = SearchResultSerializer(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"])
    def follow(self, request, pk=None):
        result = self.get_object()
        try:
            suggestion = derive_topic_from_result(result)
        except AIUnavailable as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        base_name = (suggestion["name"] or f"Follow-up: {result.title}").strip()[:170] or "Followed topic"
        name = base_name
        suffix = 2
        while SearchTopic.objects.filter(owner=request.user, name=name).exists():
            name = f"{base_name} ({suffix})"[:180]
            suffix += 1

        if result.topic_id:
            source_scopes = list(result.topic.source_scopes.filter(enabled=True))
        else:
            source_scopes = list(owned_source_scopes(request.user).filter(enabled=True))
        if not source_scopes:
            return Response(
                {"error": "No enabled source scopes available to attach to the new topic."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        topic = SearchTopic.objects.create(
            owner=request.user,
            name=name,
            description=suggestion["description"],
            queries=suggestion["queries"] or [result.title[:180]],
            category_terms=suggestion["category_terms"],
            lookback_days=30,
            schedule_every=1,
            schedule_unit=SearchTopic.ScheduleUnit.DAYS,
            include_in_press_review=True,
            origin_kind=SearchTopic.OriginKind.FOLLOWED,
            origin_result=result,
        )
        topic.source_scopes.set(source_scopes)
        run_topic_search_task.delay(topic.pk)
        return Response(
            SearchTopicSerializer(topic, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

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


class PushSubscriptionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = PushSubscription.objects.none()
    serializer_class = PushSubscriptionSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        return PushSubscription.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        endpoint = self.request.data.get("endpoint", "")
        PushSubscription.objects.filter(user=self.request.user, endpoint=endpoint).delete()
        serializer.save(user=self.request.user)
