from django.conf import settings
from django.db import models

from .base import TimestampedModel


class CloudflareAccessIdentity(TimestampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cloudflare_access_identities",
    )
    subject = models.CharField(max_length=255, unique=True)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["subject"]

    def __str__(self):
        return self.email or self.subject


class PushSubscription(TimestampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
    )
    endpoint = models.TextField(unique=True)
    p256dh = models.TextField()
    auth = models.TextField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.endpoint[:60]}"
