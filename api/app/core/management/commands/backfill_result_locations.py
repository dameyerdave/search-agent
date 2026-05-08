from django.core.management.base import BaseCommand

from core.models import SearchResult
from core.result_locations import refresh_result_locations


class Command(BaseCommand):
    help = "Extract and geocode stored places for existing search results."

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
            help="Recompute locations even when a result already has a matching signature.",
        )

    def handle(self, *args, **options):
        queryset = (
            SearchResult.objects.select_related("topic")
            .prefetch_related("locations")
            .order_by("-published_at", "-first_seen_at", "-id")
        )

        topic_slug = (options.get("topic_slug") or "").strip()
        if topic_slug:
            queryset = queryset.filter(topic__slug=topic_slug)

        limit = max(int(options.get("limit") or 0), 0)
        if limit:
            queryset = queryset[:limit]

        processed = 0
        mapped = 0
        changed = 0
        force_refresh = bool(options.get("force"))

        for result in queryset.iterator(chunk_size=100):
            previous_signature = result.location_signature
            previous_location_count = len(result.locations.all())
            if force_refresh and previous_signature:
                result.location_signature = ""

            locations = refresh_result_locations(result)
            processed += 1
            if locations:
                mapped += 1
            if result.location_signature != previous_signature or len(locations) != previous_location_count:
                changed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {processed} results, mapped {mapped}, changed {changed}."
            )
        )
