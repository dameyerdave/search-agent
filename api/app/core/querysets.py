from django.db.models import Count, Q

from .models import SearchResult, SearchRun, SearchTopic, SourceScope


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
    return SearchResult.objects.select_related("topic", "source_scope", "last_run").filter(
        topic__owner=user
    )
