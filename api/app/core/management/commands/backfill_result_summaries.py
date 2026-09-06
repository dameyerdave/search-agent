from django.core.management.base import BaseCommand

from core.models import SearchResult
from core.result_summaries import MAX_RESULTS_PER_BATCH, generate_summaries_for_results


class Command(BaseCommand):
    help = "Generate AI summaries for existing search results that don't have one yet."

    def add_arguments(self, parser):
        parser.add_argument(
            "--topic",
            dest="topic_slug",
            help="Only process results for the given topic slug.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Maximum number of results to process.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Regenerate summaries even when a result already has a matching signature.",
        )

    def handle(self, *args, **options):
        queryset = SearchResult.objects.select_related("topic").order_by(
            "-published_at", "-first_seen_at", "-id"
        )

        topic_slug = (options.get("topic_slug") or "").strip()
        if topic_slug:
            queryset = queryset.filter(topic__slug=topic_slug)

        limit = max(int(options.get("limit") or 0), 0)
        if limit:
            queryset = queryset[:limit]

        force_refresh = bool(options.get("force"))

        processed = 0
        summarized = 0
        batch = []
        for result in queryset.iterator(chunk_size=100):
            if force_refresh and result.summary_signature:
                result.summary_signature = ""
            batch.append(result)
            processed += 1
            if len(batch) >= MAX_RESULTS_PER_BATCH:
                summarized += generate_summaries_for_results(batch)
                batch = []

        if batch:
            summarized += generate_summaries_for_results(batch)

        self.stdout.write(
            self.style.SUCCESS(f"Processed {processed} results, summarized {summarized}.")
        )
