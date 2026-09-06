from __future__ import annotations

from .ai_client import call_swissai_chat, extract_json

MAX_TEXT_EXCERPT = 4000

CATEGORY_KEYS = ("keywords", "people", "companies", "locations", "regions", "events")

SYSTEM_PROMPT = (
    "You help set up a recurring web search monitoring topic. Given the supplied text, propose: "
    "a short topic name (a few words), a one-sentence description, up to 5 short search-query "
    "phrases that would find similar/related coverage, and categorized entities that refine the "
    "search: keywords, people, companies, locations (specific places), regions (broader areas, "
    "countries, continents), and events (named events, incidents, occasions). Only include terms "
    "actually grounded in the supplied text - do not invent entities that aren't mentioned or "
    "clearly implied.\n\n"
    "Respond with ONLY a JSON object, no prose, no markdown fences, with exactly these keys: "
    '"name" (string), "description" (string), "queries" (array of strings, up to 5), and '
    '"category_terms" (an object with keys "keywords", "people", "companies", "locations", '
    '"regions", "events", each an array of strings - use an empty array for any category with '
    "nothing relevant)."
)


def _empty_category_terms() -> dict[str, list[str]]:
    return {key: [] for key in CATEGORY_KEYS}


def _clean_string_list(values, *, limit: int | None = None) -> list[str]:
    cleaned = []
    for value in values or []:
        text = str(value).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned[:limit] if limit else cleaned


def suggest_topic_from_text(text: str, *, title: str = "") -> dict:
    """Ask the AI to propose a topic name/description/queries/categories from arbitrary text."""
    excerpt = (text or "").strip()[:MAX_TEXT_EXCERPT]
    user_prompt = f"Title: {title}\n\nText:\n{excerpt}" if title else f"Text:\n{excerpt}"

    raw_content = call_swissai_chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=1200,
    )
    parsed = extract_json(raw_content, expect=dict)

    category_terms = _empty_category_terms()
    raw_categories = parsed.get("category_terms")
    if isinstance(raw_categories, dict):
        for key in CATEGORY_KEYS:
            category_terms[key] = _clean_string_list(raw_categories.get(key), limit=10)

    return {
        "name": str(parsed.get("name") or "").strip()[:180],
        "description": str(parsed.get("description") or "").strip(),
        "queries": _clean_string_list(parsed.get("queries"), limit=5),
        "category_terms": category_terms,
    }


def derive_topic_from_result(result) -> dict:
    """Derive a topic suggestion from a stored SearchResult's crawled content."""
    text = result.content or result.snippet or ""
    return suggest_topic_from_text(text, title=result.title)
