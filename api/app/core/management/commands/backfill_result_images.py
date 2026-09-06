from django.core.management.base import BaseCommand

from core.models import SearchResult
from core.result_images import backfill_missing_images


class Command(BaseCommand):
    help = "Populate image_url for existing search results that don't have one yet."

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
            help="Maximum number of results to process (0 = process the entire current backlog).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Also re-check results that already have an image_url (clears it first).",
        )

    def handle(self, *args, **options):
        topic_slug = (options.get("topic_slug") or "").strip() or None

        if options.get("force"):
            queryset = SearchResult.objects.exclude(image_url="")
            if topic_slug:
                queryset = queryset.filter(topic__slug=topic_slug)
            cleared = queryset.update(image_url="")
            self.stdout.write(f"Cleared image_url on {cleared} results before re-fetching.")

        limit = int(options.get("limit") or 0)
        remaining = SearchResult.objects.filter(image_url="").exclude(url="")
        if topic_slug:
            remaining = remaining.filter(topic__slug=topic_slug)
        total_backlog = remaining.count()
        batch_size = limit or total_backlog

        updated = backfill_missing_images(batch_size, topic_slug=topic_slug)
        self.stdout.write(
            self.style.SUCCESS(f"Backlog was {total_backlog}. Populated images for {updated} results.")
        )
