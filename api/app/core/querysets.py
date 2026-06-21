from django.db.models import Count, Q

from .models import SavedFolder, SearchResult, SearchRun, SearchTopic, SourceScope


def owned_source_scopes(user):
    if not user.is_authenticated:
        return SourceScope.objects.none()
    return SourceScope.objects.filter(owner=user)


def owned_topics(user):
    if not user.is_authenticated:
        return SearchTopic.objects.none()
    return SearchTopic.objects.filter(owner=user).prefetch_related("source_scopes").annotate(
        result_count=Count("results", distinct=True),
        new_results_count=Count(
            "results",
            filter=Q(results__is_new=True),
            distinct=True,
        ),
    )


def owned_runs(user):
    if not user.is_authenticated:
        return SearchRun.objects.none()
    return SearchRun.objects.select_related("topic").filter(topic__owner=user)


def owned_results(user):
    if not user.is_authenticated:
        return SearchResult.objects.none()
    return SearchResult.objects.select_related("topic", "source_scope", "last_run", "folder").filter(
        Q(topic__owner=user) | Q(owner=user, topic__isnull=True)
    )


def owned_folders(user):
    if not user.is_authenticated:
        return SavedFolder.objects.none()
    return SavedFolder.objects.filter(owner=user).annotate(
        result_count=Count("results", filter=Q(results__is_saved=True), distinct=True)
    )
