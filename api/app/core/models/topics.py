from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from .base import TimestampedModel
from .sources import SourceScope


class SearchTopic(TimestampedModel):
    class RunStatus(models.TextChoices):
        IDLE = "idle", "Idle"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        LIMITED = "limited", "Limited"

    class ScheduleUnit(models.TextChoices):
        MINUTES = "minutes", "Minutes"
        HOURS = "hours", "Hours"
        DAYS = "days", "Days"
        WEEKS = "weeks", "Weeks"

    class OriginKind(models.TextChoices):
        MANUAL = "manual", "Manual"
        FOLLOWED = "followed", "Followed"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="search_topics",
    )
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)
    queries = models.JSONField(default=list, blank=True)
    required_terms = models.JSONField(default=list, blank=True)
    excluded_terms = models.JSONField(default=list, blank=True)
    lookback_days = models.PositiveSmallIntegerField(
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(3650)],
    )
    schedule_every = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10000)],
    )
    schedule_unit = models.CharField(
        max_length=16,
        choices=ScheduleUnit.choices,
        default=ScheduleUnit.DAYS,
    )
    max_results_per_query = models.PositiveSmallIntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
    )
    notes = models.TextField(blank=True)
    category_terms = models.JSONField(default=dict, blank=True)
    include_in_press_review = models.BooleanField(default=True)
    origin_kind = models.CharField(
        max_length=16,
        choices=OriginKind.choices,
        default=OriginKind.MANUAL,
    )
    origin_result = models.ForeignKey(
        "core.SearchResult",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="derived_topics",
    )
    source_scopes = models.ManyToManyField(SourceScope, related_name="topics", blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_new_results_at = models.DateTimeField(null=True, blank=True)
    last_run_status = models.CharField(
        max_length=32,
        choices=RunStatus.choices,
        default=RunStatus.IDLE,
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                name="unique_search_topic_name_per_owner",
            ),
            models.UniqueConstraint(
                fields=["owner", "slug"],
                name="unique_search_topic_slug_per_owner",
            ),
        ]

    def __str__(self):
        return self.name

    def schedule_delta(self):
        if self.schedule_unit == self.ScheduleUnit.MINUTES:
            return timedelta(minutes=self.schedule_every)
        if self.schedule_unit == self.ScheduleUnit.HOURS:
            return timedelta(hours=self.schedule_every)
        if self.schedule_unit == self.ScheduleUnit.WEEKS:
            return timedelta(weeks=self.schedule_every)
        return timedelta(days=self.schedule_every)

    def compute_next_run_at(self, reference_time=None):
        anchor = reference_time or timezone.now()
        return anchor + self.schedule_delta()

    @property
    def schedule_description(self):
        unit_label = self.schedule_unit[:-1] if self.schedule_every == 1 else self.schedule_unit
        return f"Every {self.schedule_every} {unit_label}"

    def set_next_run(self, reference_time=None):
        self.next_run_at = self.compute_next_run_at(reference_time) if self.enabled else None
        return self.next_run_at

    def save(self, *args, **kwargs):
        schedule_reset_required = False
        update_fields = kwargs.get("update_fields")
        if self.pk:
            previous = (
                SearchTopic.objects.filter(pk=self.pk)
                .values("enabled", "schedule_every", "schedule_unit", "next_run_at")
                .first()
            )
            schedule_reset_required = (
                previous is None
                or previous["enabled"] != self.enabled
                or previous["schedule_every"] != self.schedule_every
                or previous["schedule_unit"] != self.schedule_unit
                or (self.enabled and previous["next_run_at"] is None)
            )
        else:
            schedule_reset_required = True

        if not self.slug:
            base_slug = slugify(self.name) or "topic"
            candidate = base_slug
            counter = 2
            slug_queryset = SearchTopic.objects.exclude(pk=self.pk)
            if self.owner_id:
                slug_queryset = slug_queryset.filter(owner_id=self.owner_id)
            while slug_queryset.filter(slug=candidate).exists():
                candidate = f"{base_slug}-{counter}"
                counter += 1
            self.slug = candidate

        if schedule_reset_required:
            self.set_next_run()
            if update_fields is not None:
                updated = set(update_fields)
                updated.add("next_run_at")
                kwargs["update_fields"] = updated

        super().save(*args, **kwargs)


class SearchProviderConfig(TimestampedModel):
    name = models.CharField(max_length=40, unique=True, default="searxng")
    enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @classmethod
    def load(cls):
        config, _ = cls.objects.get_or_create(name="searxng")
        return config


class SearchRun(TimestampedModel):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        LIMITED = "limited", "Limited"

    topic = models.ForeignKey(
        SearchTopic,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    source_scope_count = models.PositiveIntegerField(default=0)
    request_count = models.PositiveIntegerField(default=0)
    pages_crawled = models.PositiveIntegerField(default=0)
    results_collected = models.PositiveIntegerField(default=0)
    new_results_count = models.PositiveIntegerField(default=0)
    query_snapshot = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.topic.name} @ {self.started_at:%Y-%m-%d %H:%M}"


class TopicTimelineSummary(TimestampedModel):
    topic = models.OneToOneField(
        SearchTopic,
        on_delete=models.CASCADE,
        related_name="timeline_summary",
    )
    generated_at = models.DateTimeField(default=timezone.now)
    model_name = models.CharField(max_length=120, blank=True)
    entries = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"Timeline for {self.topic.name}"
