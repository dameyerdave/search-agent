from __future__ import annotations

import re
from urllib.parse import urljoin

import httpx

from .models import SearchResult

MAX_IMAGE_BACKFILL_BATCH = 25
FETCH_TIMEOUT_S = 8.0
MAX_HTML_SCAN_BYTES = 200_000

_META_IMAGE_PATTERNS = (
    re.compile(
        r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)["\']',
        re.IGNORECASE,
    ),
    re.compile(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image(?::secure_url)?["\']',
        re.IGNORECASE,
    ),
    re.compile(
        r'<meta[^>]+(?:name|property)=["\']twitter:image(?::src)?["\'][^>]+content=["\']([^"\']+)["\']',
        re.IGNORECASE,
    ),
)


def fetch_page_image(url: str) -> str:
    """Best-effort, lightweight og:image/twitter:image lookup via a plain GET (no browser)."""
    try:
        response = httpx.get(
            url,
            timeout=FETCH_TIMEOUT_S,
            follow_redirects=True,
            headers={"User-Agent": "search-agent/1.0 (+image preview fetcher)"},
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return ""

    html = response.text[:MAX_HTML_SCAN_BYTES]
    for pattern in _META_IMAGE_PATTERNS:
        match = pattern.search(html)
        if match:
            candidate = match.group(1).strip()
            if candidate:
                return urljoin(str(response.url), candidate)
    return ""


def backfill_missing_images(limit: int = MAX_IMAGE_BACKFILL_BATCH, *, topic_slug: str | None = None) -> int:
    """Populate image_url for a batch of results that don't have one yet.

    Cheap tier first (the SearxNG thumbnail already stored in favicon_url), then a
    lightweight direct fetch of the page's og:image/twitter:image meta tags - no
    browser automation, unlike the Crawl4AI path used during a topic's own crawl.
    """
    queryset = SearchResult.objects.filter(image_url="").exclude(url="").order_by("-first_seen_at")
    if topic_slug:
        queryset = queryset.filter(topic__slug=topic_slug)

    updated = []
    for result in queryset[:limit]:
        image_url = result.favicon_url or fetch_page_image(result.url)
        if image_url:
            result.image_url = image_url
            updated.append(result)

    if updated:
        SearchResult.objects.bulk_update(updated, ["image_url"])
    return len(updated)
