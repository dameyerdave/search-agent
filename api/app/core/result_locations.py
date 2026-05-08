from __future__ import annotations

import hashlib
import re
from decimal import Decimal, InvalidOperation

import httpx
from django.conf import settings
from django.core.cache import cache

from .models import SearchResult, SearchResultLocation

LOCATION_CACHE_PREFIX = "core:result-locations:v1"
LOCATION_CACHE_TTL_S = 60 * 60 * 24 * 30
LOCATION_CACHE_MISS_TTL_S = 60 * 60 * 12
MAX_LOCATION_TEXT_LENGTH = 6000
MAX_LOCATION_CANDIDATES = 8
MAX_RESULT_LOCATIONS = 5

LOCATION_STOP_WORDS = {
    "april",
    "august",
    "december",
    "february",
    "friday",
    "january",
    "july",
    "june",
    "march",
    "monday",
    "november",
    "october",
    "saturday",
    "september",
    "sunday",
    "thursday",
    "today",
    "tomorrow",
    "tuesday",
    "wednesday",
    "yesterday",
}
LOCATION_JOINERS = {"and", "de", "del", "du", "la", "of", "the", "van", "von"}
LOCATION_ALIAS_MAP = {
    "u.s.": "United States",
    "u.s": "United States",
    "usa": "United States",
    "us": "United States",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "uae": "United Arab Emirates",
}
SUPPORTED_PLACE_TYPES = {
    "administrative",
    "archipelago",
    "borough",
    "city",
    "continent",
    "country",
    "county",
    "district",
    "hamlet",
    "island",
    "locality",
    "municipality",
    "neighbourhood",
    "province",
    "quarter",
    "region",
    "state",
    "suburb",
    "town",
    "village",
}
WHITESPACE_RE = re.compile(r"\s+")
CONTEXT_LOCATION_RE = re.compile(
    r"\b(?:in|at|from|near|across|around|outside|inside|within|throughout|toward|to|into)\s+"
    r"([A-Z][A-Za-z'’.-]*(?:[\s-]+(?:[A-Z][A-Za-z'’.-]*|and|de|del|du|la|of|the|van|von)){0,5})"
)
COMMA_LOCATION_RE = re.compile(
    r"\b([A-Z][A-Za-z'’.-]+(?:[\s-]+[A-Z][A-Za-z'’.-]+){0,3},\s*"
    r"[A-Z][A-Za-z'’.-]+(?:[\s-]+[A-Z][A-Za-z'’.-]+){0,3})\b"
)
PROPER_NOUN_LOCATION_RE = re.compile(
    r"\b([A-Z][A-Za-z'’.-]+(?:[\s-]+(?:[A-Z][A-Za-z'’.-]+|de|del|du|la|of|the|van|von)){0,3})\b"
)


class GeocodingUnavailable(RuntimeError):
    pass


def build_location_signature(result: SearchResult) -> str:
    text = " ".join(
        part.strip()
        for part in [
            result.title or "",
            result.snippet or "",
            (result.content or "")[:MAX_LOCATION_TEXT_LENGTH],
        ]
        if part and part.strip()
    )
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def normalize_location_candidate(value: str) -> str:
    candidate = WHITESPACE_RE.sub(" ", str(value or "").strip()).strip(" ,.;:!?()[]{}\"'")
    if not candidate:
        return ""

    candidate = LOCATION_ALIAS_MAP.get(candidate.lower(), candidate)
    parts = [part for part in re.split(r"[\s-]+", candidate) if part]
    if not parts or len(parts) > 6:
        return ""
    if not any(char.isalpha() for char in candidate):
        return ""

    if len(parts) == 1 and parts[0].lower() in LOCATION_STOP_WORDS:
        return ""

    cleaned_parts = []
    for index, part in enumerate(parts):
        lower = part.lower()
        if lower in LOCATION_JOINERS and index not in {0, len(parts) - 1}:
            cleaned_parts.append(lower)
            continue
        if not any(char.isalpha() for char in part):
            return ""
        cleaned_parts.append(part)

    normalized = " ".join(cleaned_parts).strip()
    return WHITESPACE_RE.sub(" ", normalized)


def extract_location_candidates(title: str, snippet: str = "", content: str = "") -> list[str]:
    scored_candidates: dict[str, int] = {}
    long_text = "\n".join(filter(None, [title, snippet, content[:MAX_LOCATION_TEXT_LENGTH]]))
    short_text = "\n".join(filter(None, [title, snippet[:240]]))

    def add_candidate(raw_value: str, score: int):
        candidate = normalize_location_candidate(raw_value)
        if not candidate:
            return
        scored_candidates[candidate] = max(scored_candidates.get(candidate, 0), score)

    for match in COMMA_LOCATION_RE.finditer(long_text):
        add_candidate(match.group(1), 4)

    for text in filter(None, [title, snippet, content[:MAX_LOCATION_TEXT_LENGTH]]):
        for match in CONTEXT_LOCATION_RE.finditer(text):
            add_candidate(match.group(1), 3)

    for match in PROPER_NOUN_LOCATION_RE.finditer(short_text):
        add_candidate(match.group(1), 1)

    ranked = sorted(scored_candidates.items(), key=lambda item: (-item[1], item[0].lower()))
    return [candidate for candidate, _score in ranked]


def normalize_location_name(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value.strip().lower())


def serialize_coordinate(value: str | float | Decimal | None) -> str | None:
    try:
        return str(Decimal(str(value)).quantize(Decimal("0.000001")))
    except (InvalidOperation, TypeError, ValueError):
        return None


def is_supported_place(payload: dict) -> bool:
    place_type = str(payload.get("type") or payload.get("addresstype") or "").strip().lower()
    osm_class = str(payload.get("class") or "").strip().lower()
    return place_type in SUPPORTED_PLACE_TYPES or (
        osm_class == "boundary" and place_type == "administrative"
    )


def short_location_label(payload: dict, fallback: str) -> str:
    label = str(payload.get("name") or "").strip()
    if label:
        return label[:180]

    display_name = str(payload.get("display_name") or "").strip()
    if display_name:
        return display_name.split(",", 1)[0].strip()[:180]
    return fallback[:180]


def geocode_location_candidate(candidate: str) -> dict | None:
    normalized_candidate = normalize_location_candidate(candidate)
    if not normalized_candidate:
        return None

    cache_hash = hashlib.sha1(normalized_candidate.lower().encode("utf-8")).hexdigest()
    cache_key = f"{LOCATION_CACHE_PREFIX}:{cache_hash}"
    cached = cache.get(cache_key)
    if isinstance(cached, dict):
        if cached.get("_missing"):
            return None
        return cached

    base_url = getattr(
        settings,
        "NOMINATIM_BASE_URL",
        "https://nominatim.openstreetmap.org",
    ).rstrip("/")
    timeout_s = float(getattr(settings, "NOMINATIM_TIMEOUT_S", 5.0))
    user_agent = getattr(
        settings,
        "NOMINATIM_USER_AGENT",
        "search-agent/1.0 (OpenStreetMap result geocoder)",
    )

    try:
        response = httpx.get(
            f"{base_url}/search",
            params={
                "q": normalized_candidate,
                "format": "jsonv2",
                "limit": 3,
                "addressdetails": 0,
                "accept-language": "en",
            },
            headers={"Accept": "application/json", "User-Agent": user_agent},
            timeout=timeout_s,
        )
        if response.status_code in {429, 500, 502, 503, 504}:
            raise GeocodingUnavailable(f"Nominatim temporarily unavailable for {normalized_candidate}.")
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise GeocodingUnavailable(
            f"Nominatim lookup failed for {normalized_candidate}."
        ) from exc

    payload = response.json()
    if not isinstance(payload, list):
        payload = []

    match = next((item for item in payload if is_supported_place(item)), None)
    latitude = serialize_coordinate(match.get("lat")) if match else None
    longitude = serialize_coordinate(match.get("lon")) if match else None
    if not match or not latitude or not longitude:
        cache.set(cache_key, {"_missing": True}, timeout=LOCATION_CACHE_MISS_TTL_S)
        return None

    resolved = {
        "name": short_location_label(match, normalized_candidate),
        "normalized_name": normalize_location_name(short_location_label(match, normalized_candidate)),
        "display_name": str(match.get("display_name") or normalized_candidate).strip()[:255],
        "latitude": latitude,
        "longitude": longitude,
        "place_type": str(match.get("type") or match.get("addresstype") or "").strip()[:40],
        "importance": float(match.get("importance") or 0) if match.get("importance") else None,
    }
    cache.set(cache_key, resolved, timeout=LOCATION_CACHE_TTL_S)
    return resolved


def refresh_result_locations(result: SearchResult) -> list[SearchResultLocation]:
    signature = build_location_signature(result)
    existing_locations = list(result.locations.all())
    if signature == result.location_signature:
        return existing_locations

    candidates = extract_location_candidates(
        title=result.title,
        snippet=result.snippet,
        content=result.content,
    )

    resolved_locations = []
    seen_locations = set()
    try:
        for candidate in candidates[:MAX_LOCATION_CANDIDATES]:
            resolved = geocode_location_candidate(candidate)
            if not resolved:
                continue

            location_key = (
                resolved["normalized_name"],
                resolved["latitude"],
                resolved["longitude"],
            )
            if location_key in seen_locations:
                continue
            seen_locations.add(location_key)
            resolved_locations.append(resolved)
            if len(resolved_locations) >= MAX_RESULT_LOCATIONS:
                break
    except GeocodingUnavailable:
        return existing_locations

    result.location_signature = signature
    result.save(update_fields=["location_signature", "updated_at"])
    result.locations.all().delete()

    location_records = [
        SearchResultLocation(
            result=result,
            name=payload["name"],
            normalized_name=payload["normalized_name"],
            display_name=payload["display_name"],
            latitude=Decimal(payload["latitude"]),
            longitude=Decimal(payload["longitude"]),
            place_type=payload["place_type"],
            importance=payload["importance"],
        )
        for payload in resolved_locations
    ]
    if location_records:
        SearchResultLocation.objects.bulk_create(location_records)
    return location_records


def build_result_location_map_payload(results_queryset) -> dict:
    ordered_results = list(
        results_queryset.prefetch_related("locations").order_by(
            "-is_new",
            "-published_at",
            "-first_seen_at",
        )
    )

    markers_by_key: dict[str, dict] = {}
    mapped_result_ids = set()

    for result in ordered_results:
        locations = list(result.locations.all())
        if not locations:
            continue

        mapped_result_ids.add(result.id)
        preview = {
            "id": result.id,
            "title": result.title,
            "url": result.url,
            "topic_name": result.topic.name,
            "source_scope_name": result.source_scope.name if result.source_scope else None,
            "domain": result.domain,
            "published_at": result.published_at,
            "is_new": result.is_new,
        }
        for location in locations:
            marker_key = (
                f"{location.normalized_name}:{location.latitude}:{location.longitude}"
            )
            marker = markers_by_key.setdefault(
                marker_key,
                {
                    "id": marker_key,
                    "name": location.name,
                    "display_name": location.display_name or location.name,
                    "latitude": float(location.latitude),
                    "longitude": float(location.longitude),
                    "place_type": location.place_type,
                    "results": [],
                    "_result_ids": set(),
                    "_preview_ids": set(),
                },
            )
            marker["_result_ids"].add(result.id)
            if (
                result.id not in marker["_preview_ids"]
                and len(marker["results"]) < 12
            ):
                marker["_preview_ids"].add(result.id)
                marker["results"].append(preview)

    markers = []
    for marker in markers_by_key.values():
        result_ids = marker.pop("_result_ids")
        marker.pop("_preview_ids")
        related_result_count = len(result_ids)
        marker["related_result_count"] = related_result_count
        marker["remaining_result_count"] = max(
            related_result_count - len(marker["results"]),
            0,
        )
        markers.append(marker)

    markers.sort(key=lambda item: (-item["related_result_count"], item["name"].lower()))
    return {
        "result_count": len(ordered_results),
        "mapped_result_count": len(mapped_result_ids),
        "location_count": len(markers),
        "markers": markers,
    }
