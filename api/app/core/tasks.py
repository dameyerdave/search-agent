from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from celery import shared_task

from .models import SearchRun, SearchTopic
from .services import run_topic_search


@shared_task
def run_topic_search_task(topic_id: int):
    topic = SearchTopic.objects.get(pk=topic_id)
    if not topic.enabled:
        return {"topic_id": topic_id, "status": "skipped", "reason": "topic disabled"}
    run = run_topic_search(topic)
    return {"run_id": run.id, "status": run.status}


@shared_task
def dispatch_due_topic_searches(batch_size: int = 25):
    now = timezone.now()
    queued_topic_ids = []

    with transaction.atomic():
        due_topics = list(
            SearchTopic.objects.select_for_update()
            .filter(enabled=True)
            .filter(Q(next_run_at__lte=now) | Q(next_run_at__isnull=True))
            .order_by("next_run_at", "name")[:batch_size]
        )
        running_topic_ids = set(
            SearchRun.objects.filter(
                topic_id__in=[topic.pk for topic in due_topics],
                status=SearchRun.Status.RUNNING,
            ).values_list("topic_id", flat=True)
        )

        for topic in due_topics:
            if topic.pk in running_topic_ids:
                continue
            topic.set_next_run(now)
            topic.save(update_fields=["next_run_at", "updated_at"])
            queued_topic_ids.append(topic.pk)

    for topic_id in queued_topic_ids:
        run_topic_search_task.delay(topic_id)

    return {
        "queued_topic_ids": queued_topic_ids,
        "queued_count": len(queued_topic_ids),
        "checked_at": now.isoformat(),
    }


@shared_task
def run_all_topic_searches():
    summaries = []
    for topic in SearchTopic.objects.filter(enabled=True).order_by("name"):
        run = run_topic_search(topic)
        summaries.append(
            {
                "topic": topic.slug,
                "run_id": run.id,
                "status": run.status,
                "new_results_count": run.new_results_count,
            }
        )
    return summaries
