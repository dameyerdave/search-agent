from __future__ import annotations

from datetime import date as date_cls
from datetime import time as time_cls

from django.conf import settings
from django.utils import timezone

from .ai_client import AIUnavailable as TimelineUnavailable
from .ai_client import call_swissai_chat, extract_json
from .models import SearchTopic, TopicTimelineSummary

MAX_RESULTS_FOR_TIMELINE = 40
MAX_CONTENT_EXCERPT = 400
MAX_SNIPPET_EXCERPT = 250

SYSTEM_PROMPT = (
    "You build factual timelines from web search results collected for a monitored topic. "
    "You will be given a list of search results, each with an id, a known publication date "
    "(known_date), any real-world places already identified in the text (known_places), a "
    "title, and a text excerpt. Extract concrete, dated events that are actually described in "
    "the text - do not invent facts. Prefer known_date/known_places as the event's date/place "
    "when they clearly refer to the event itself; otherwise look for a more specific date or "
    "place stated in the text. Merge results describing the same event into one timeline entry "
    "and list every matching result id. Order entries chronologically, earliest first.\n\n"
    'Respond with ONLY a JSON array, no prose, no markdown fences. Each element must have '
    'exactly these keys: "date" (YYYY-MM-DD or "" if unknown), "time" (24h HH:MM or "" if '
    'unknown), "place" (short place name or "" if unknown), "summary" (one concise sentence in '
    'the same language as the source results), "result_ids" (array of integer ids backing this '
    "entry). If no concrete dated event can be found, respond with []."
)


def _format_result_block(result) -> str:
    locations = list(result.locations.all())
    place_names = ", ".join(location.name for location in locations[:3])
    published = result.published_at.isoformat() if result.published_at else ""
    snippet = (result.snippet or "").strip()[:MAX_SNIPPET_EXCERPT]
    content_excerpt = (result.content or "").strip()[:MAX_CONTENT_EXCERPT]

    lines = [
        f"id: {result.id}",
        f"known_date: {published or 'unknown'}",
        f"known_places: {place_names or 'unknown'}",
        f"title: {result.title}",
        f"snippet: {snippet or 'unknown'}",
    ]
    if content_excerpt and content_excerpt != snippet:
        lines.append(f"excerpt: {content_excerpt}")
    return "\n".join(lines)


def _parse_timeline_entries(raw_text: str) -> list[dict]:
    parsed = extract_json(raw_text, expect=list)

    entries = []
    for index, item in enumerate(parsed):
        if not isinstance(item, dict):
            continue
        summary = str(item.get("summary") or "").strip()
        if not summary:
            continue
        result_ids = [rid for rid in (item.get("result_ids") or []) if isinstance(rid, int)]
        entries.append(
            {
                "date": str(item.get("date") or "").strip(),
                "time": str(item.get("time") or "").strip(),
                "place": str(item.get("place") or "").strip(),
                "summary": summary,
                "result_ids": result_ids,
                "_source_order": index,
            }
        )
    return entries


def _sort_key(entry: dict):
    parsed_date = None
    if entry["date"]:
        try:
            parsed_date = date_cls.fromisoformat(entry["date"])
        except ValueError:
            parsed_date = None

    if parsed_date is None:
        return (1, entry["_source_order"], time_cls.min)

    parsed_time = time_cls.min
    if entry["time"]:
        try:
            parsed_time = time_cls.fromisoformat(entry["time"])
        except ValueError:
            parsed_time = time_cls.min
    return (0, parsed_date, parsed_time)


def _enrich_place(entry: dict, results_by_id: dict) -> tuple[float | None, float | None]:
    normalized_place = entry["place"].strip().lower()
    if not normalized_place:
        return None, None

    for result_id in entry["result_ids"]:
        result = results_by_id.get(result_id)
        if not result:
            continue
        for location in result.locations.all():
            if (
                normalized_place in location.normalized_name
                or location.normalized_name in normalized_place
            ):
                return float(location.latitude), float(location.longitude)
    return None, None


def generate_topic_timeline(topic: SearchTopic) -> TopicTimelineSummary:
    results = list(
        topic.results.all()
        .prefetch_related("locations")
        .order_by("-published_at", "-first_seen_at")[:MAX_RESULTS_FOR_TIMELINE]
    )
    if not results:
        raise TimelineUnavailable("This topic has no stored results yet.")

    results_by_id = {result.id: result for result in results}
    blocks = "\n---\n".join(_format_result_block(result) for result in results)
    user_prompt = f"Topic: {topic.name}\n\nSearch results:\n{blocks}"

    raw_content = call_swissai_chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )
    parsed_entries = _parse_timeline_entries(raw_content)
    parsed_entries = [
        entry
        for entry in parsed_entries
        if not entry["result_ids"] or any(rid in results_by_id for rid in entry["result_ids"])
    ]
    parsed_entries.sort(key=_sort_key)

    entries = []
    for order, entry in enumerate(parsed_entries, start=1):
        result_ids = [rid for rid in entry["result_ids"] if rid in results_by_id]
        latitude, longitude = _enrich_place(entry, results_by_id)
        entries.append(
            {
                "order": order,
                "date": entry["date"],
                "time": entry["time"],
                "place": entry["place"],
                "summary": entry["summary"],
                "latitude": latitude,
                "longitude": longitude,
                "results": [
                    {
                        "id": rid,
                        "title": results_by_id[rid].title,
                        "url": results_by_id[rid].url,
                    }
                    for rid in result_ids
                ],
            }
        )

    summary, _created = TopicTimelineSummary.objects.update_or_create(
        topic=topic,
        defaults={
            "generated_at": timezone.now(),
            "model_name": settings.SWISSAI_MODEL,
            "entries": entries,
        },
    )
    return summary
