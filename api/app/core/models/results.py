from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .base import TimestampedModel
from .sources import SourceScope
from .topics import SearchRun, SearchTopic


class SavedFolder(TimestampedModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_folders",
    )
    name = models.CharField(max_length=200)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "name"], name="unique_folder_per_owner")
        ]

    def __str__(self):
        return self.name


class SearchResult(TimestampedModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookmarks",
        null=True,
        blank=True,
    )
    topic = models.ForeignKey(
        SearchTopic,
        on_delete=models.CASCADE,
        related_name="results",
        null=True,
        blank=True,
    )
    source_scope = models.ForeignKey(
        SourceScope,
        on_delete=models.SET_NULL,
        related_name="results",
        null=True,
        blank=True,
    )
    last_run = models.ForeignKey(
        SearchRun,
        on_delete=models.SET_NULL,
        related_name="results",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=500)
    url = models.URLField(max_length=1000)
    normalized_url = models.CharField(max_length=1000)
    domain = models.CharField(max_length=255, blank=True)
    snippet = models.TextField(blank=True)
    content = models.TextField(blank=True)
    favicon_url = models.URLField(max_length=1000, blank=True)
    score = models.FloatField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    matched_queries = models.JSONField(default=list, blank=True)
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    is_new = models.BooleanField(default=True)
    is_saved = models.BooleanField(default=False, db_index=True)
    saved_title = models.CharField(max_length=500, blank=True)
    folder = models.ForeignKey(
        SavedFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="results",
    )
    location_signature = models.CharField(max_length=40, blank=True)
    raw_result = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-is_new", "-published_at", "-first_seen_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["topic", "normalized_url"],
                condition=Q(topic__isnull=False),
                name="unique_result_per_topic_url",
            ),
            models.UniqueConstraint(
                fields=["owner", "normalized_url"],
                condition=Q(topic__isnull=True),
                name="unique_bookmark_per_owner_url",
            ),
        ]
        indexes = [
            models.Index(fields=["topic", "is_new"]),
            models.Index(fields=["domain"]),
            models.Index(fields=["published_at"]),
        ]

    def __str__(self):
        return self.title


class SearchResultLocation(TimestampedModel):
    result = models.ForeignKey(
        SearchResult,
        on_delete=models.CASCADE,
        related_name="locations",
    )
    name = models.CharField(max_length=180)
    normalized_name = models.CharField(max_length=180)
    display_name = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    place_type = models.CharField(max_length=40, blank=True)
    importance = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["name", "latitude", "longitude"]
        constraints = [
            models.UniqueConstraint(
                fields=["result", "normalized_name", "latitude", "longitude"],
                name="unique_result_location_per_result",
            )
        ]
        indexes = [
            models.Index(fields=["normalized_name"]),
            models.Index(fields=["latitude", "longitude"]),
        ]

    def __str__(self):
        return f"{self.name} @ {self.latitude}, {self.longitude}"
