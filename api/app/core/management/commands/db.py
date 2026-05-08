import traceback

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection, connections

from core.models import SearchProviderConfig, SearchTopic, SourceScope


class Command(BaseCommand):
    def get_seed_owner(self):
        User = get_user_model()
        return User.objects.filter(is_superuser=True).order_by("id").first() or User.objects.order_by(
            "id"
        ).first()

    def add_arguments(self, parser):
        parser.add_argument("action", type=str, help="The action to execute")

    def init(self):
        owner = self.get_seed_owner()
        SearchProviderConfig.objects.update_or_create(
            name="searxng",
            defaults={
                "enabled": True,
            },
        )

        if owner is None:
            self.stdout.write(
                self.style.WARNING(
                    "No Django user exists yet, so sample scopes and topics were skipped."
                )
            )
            return

        public_scope, _ = SourceScope.objects.update_or_create(
            owner=owner,
            name="Public Web",
            defaults={
                "description": "General-purpose public web search across public resources.",
                "kind": SourceScope.Kind.PUBLIC,
                "enabled": True,
                "searxng_categories": ["general", "news"],
                "use_all_categories": True,
                "use_all_engines": True,
                "searxng_engines": [],
                "language": "",
                "safe_search": 0,
                "time_range": SourceScope.TimeRange.AUTO,
                "max_results": 10,
                "sort_order": 10,
                "exclude_domains": ["facebook.com", "instagram.com", "x.com"],
            },
        )
        research_scope, _ = SourceScope.objects.update_or_create(
            owner=owner,
            name="Research Repositories",
            defaults={
                "description": "Research-focused repositories, registries, and exchanges.",
                "kind": SourceScope.Kind.RESEARCH,
                "enabled": True,
                "searxng_categories": ["science", "files"],
                "use_all_categories": True,
                "use_all_engines": True,
                "searxng_engines": [],
                "language": "",
                "safe_search": 0,
                "time_range": SourceScope.TimeRange.MONTH,
                "max_results": 10,
                "sort_order": 20,
                "include_domains": [
                    "zenodo.org",
                    "figshare.com",
                    "datadryad.org",
                    "osf.io",
                    "dataverse.harvard.edu",
                    "re3data.org",
                    "eudat.eu",
                    "arxiv.org",
                    "biorxiv.org",
                ],
            },
        )
        topic, _ = SearchTopic.objects.update_or_create(
            owner=owner,
            slug="research-data-exchange-landscape",
            defaults={
                "name": "Research Data Exchange Landscape",
                "description": (
                    "Monitor public and research sources for new material about "
                    "data platforms and research data exchange formats."
                ),
                "enabled": True,
                "queries": [
                    '"data platform"',
                    '"research data exchange"',
                    '"research data exchange format"',
                ],
                "required_terms": [],
                "excluded_terms": [],
                "lookback_days": 30,
                "schedule_every": 1,
                "schedule_unit": SearchTopic.ScheduleUnit.DAYS,
                "max_results_per_query": 10,
                "notes": "Seed topic created from the user-provided example terms.",
            },
        )
        topic.source_scopes.set([public_scope, research_scope])
        self.stdout.write(self.style.SUCCESS("Search agent defaults initialized."))

    def clean(self):
        call_command("flush")
        call_command("makemigrations", "core")
        call_command("migrate")
        call_command("initadmin")
        self.init()

    def reset(self):
        """
        Resets the whole database.
        The django_extensions package must be installed!
        """
        dbname = settings.DATABASES["default"]["NAME"]
        answer = input(
            f"Do you really want to drop the database {dbname}? !!! YOU WILL LOSE ALL DATA !!! [y/N] "
        )
        if answer and len(answer) > 0 and answer[0].lower() == "y":
            with connection.cursor() as cursor:
                # First disconnect all connection except our own
                cursor.execute(
                    f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid <> pg_backend_pid() AND datname='{dbname}'"
                )
                # disconnect our own connection
                cursor.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{dbname}'"
                )
            # make sure everything is disconnected
            connections.close_all()
            # reset the database DROP / CREATE
            call_command("reset_db", "--no-input")
            self.stdout.write(
                self.style.SUCCESS(f"Successfully reset database '{dbname}'")
            )

    def handle(self, *args, **options):
        try:
            if options.get("action") == "clean":
                self.clean()
            elif options.get("action") == "init":
                self.init()
            elif options.get("action") == "reset":
                self.reset()
        except Exception as ex:
            self.stderr.write(self.style.ERROR(str(ex)))
            traceback.print_exc()
