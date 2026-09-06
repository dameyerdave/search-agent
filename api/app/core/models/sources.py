from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .base import TimestampedModel


class SourceScope(TimestampedModel):
    class Kind(models.TextChoices):
        PUBLIC = "public", "Public"
        RESEARCH = "research", "Research"
        CUSTOM = "custom", "Custom"

    class TimeRange(models.TextChoices):
        AUTO = "auto", "Auto"
        ANY = "any", "Any"
        DAY = "day", "Day"
        MONTH = "month", "Month"
        YEAR = "year", "Year"

    class ResultOrder(models.TextChoices):
        RELEVANCE = "relevance", "Relevance"
        NEWEST = "newest", "Time (newest first)"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="source_scopes",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    kind = models.CharField(
        max_length=32,
        choices=Kind.choices,
        default=Kind.PUBLIC,
    )
    enabled = models.BooleanField(default=True)
    searxng_categories = models.JSONField(default=list, blank=True)
    use_all_categories = models.BooleanField(default=True)
    use_all_engines = models.BooleanField(default=True)
    searxng_engines = models.JSONField(default=list, blank=True)
    languages = models.JSONField(default=list, blank=True)
    safe_search = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
    )
    time_range = models.CharField(
        max_length=16,
        choices=TimeRange.choices,
        default=TimeRange.AUTO,
    )
    result_order = models.CharField(
        max_length=16,
        choices=ResultOrder.choices,
        default=ResultOrder.RELEVANCE,
    )
    max_results = models.PositiveSmallIntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
    )
    include_domains = models.JSONField(default=list, blank=True)
    exclude_domains = models.JSONField(default=list, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                name="unique_source_scope_name_per_owner",
            )
        ]

    def __str__(self):
        return self.name
