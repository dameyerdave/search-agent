from __future__ import annotations

import httpx
from django.conf import settings
from django.core.cache import cache

from ..models import SearchTopic, SourceScope
from .query import clean_string_list, domain_allowed, extract_domain, normalize_url, resolve_time_range

SEARXNG_CATEGORY_BATCH_SIZE = 4
SEARXNG_CATEGORY_PRIORITY = [
    "general",
    "web",
    "news",
    "science",
    "scientific publications",
    "files",
    "repos",
    "books",
    "it",
    "software wikis",
    "apps",
]


class SearxNGClient:
    def __init__(self, base_url: str, timeout_s: float):
        if not base_url:
            raise ValueError(
                "Missing SearxNG base URL. Set SEARXNG_BASE_URL in your .env file before running searches."
            )
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def search(self, params: dict, timeout_s: float | None = None) -> dict:
        response = httpx.get(
            f"{self.base_url}/search",
            params=params,
            headers={"Accept": "application/json"},
            timeout=timeout_s or self.timeout_s,
        )
        response.raise_for_status()
        return response.json()

    def config(self) -> dict:
        response = httpx.get(
            f"{self.base_url}/config",
            headers={"Accept": "application/json"},
            timeout=min(self.timeout_s, 3.0),
        )
        response.raise_for_status()
        return response.json()


SEARXNG_CONFIG_CACHE_KEY = "core:searxng:config"


def load_searxng_config() -> dict:
    cached = cache.get(SEARXNG_CONFIG_CACHE_KEY)
    if isinstance(cached, dict):
        return cached

    try:
        client = SearxNGClient(settings.SEARXNG_BASE_URL, settings.SEARXNG_TIMEOUT_S)
        payload = client.config()
        if not isinstance(payload, dict):
            payload = {}
    except (ValueError, httpx.HTTPError):
        payload = {}

    cache.set(SEARXNG_CONFIG_CACHE_KEY, payload, timeout=300)
    return payload


def load_searxng_categories() -> list[str]:
    payload = load_searxng_config()
    return clean_string_list(payload.get("categories") or [])


def load_searxng_engines() -> list[str]:
    payload = load_searxng_config()
    raw_engines = payload.get("engines") or []
    if not isinstance(raw_engines, list):
        return []

    available = []
    seen = set()
    for item in raw_engines:
        if isinstance(item, dict):
            if not item.get("enabled", True):
                continue
            name = str(item.get("name") or "").strip()
        else:
            name = str(item).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        available.append(name)

    return sorted(available, key=str.lower)


SEARXNG_FALLBACK_LOCALES = {
    "en": "English",
    "de": "Deutsch (German)",
}


def load_searxng_locales() -> dict[str, str]:
    payload = load_searxng_config()
    raw_locales = payload.get("locales") or {}
    if not isinstance(raw_locales, dict):
        return {}

    cleaned = {}
    for code, label in raw_locales.items():
        clean_code = str(code).strip()
        if not clean_code:
            continue
        clean_label = str(label).strip() or clean_code
        cleaned[clean_code] = clean_label

    return cleaned


def load_searxng_language_options() -> list[dict[str, str]]:
    locales = load_searxng_locales() or SEARXNG_FALLBACK_LOCALES
    return [
        {"code": code, "label": label}
        for code, label in sorted(locales.items(), key=lambda item: item[1].lower())
    ]


def normalize_searxng_engines(values) -> list[str]:
    engines = clean_string_list(values)
    available = load_searxng_engines()
    if not available:
        return engines

    lookup = {engine.lower(): engine for engine in available}
    normalized = []
    seen = set()
    for engine in engines:
        match = lookup.get(engine.lower(), engine)
        if match in seen:
            continue
        seen.add(match)
        normalized.append(match)
    return normalized


def normalize_searxng_language(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    locales = load_searxng_locales()
    if not locales:
        return text

    lookup = {code.lower(): code for code in locales}
    normalized = text.replace("_", "-")
    candidates = [text, normalized]

    for candidate in candidates:
        if candidate in locales:
            return candidate
        matched = lookup.get(candidate.lower())
        if matched:
            return matched

    base_language = normalized.split("-", 1)[0]
    matched = lookup.get(base_language.lower())
    if matched:
        return matched

    return text


def normalize_searxng_languages(values) -> list[str]:
    languages = []
    seen = set()
    for value in clean_string_list(values):
        normalized = normalize_searxng_language(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            languages.append(normalized)
    return languages


def resolve_searxng_categories(values, use_all_categories: bool) -> list[str]:
    if use_all_categories:
        return load_searxng_categories()
    return clean_string_list(values)


def prioritize_searxng_categories(categories: list[str]) -> list[str]:
    ordered = []
    seen = set()
    for category in SEARXNG_CATEGORY_PRIORITY + categories:
        if category in categories and category not in seen:
            ordered.append(category)
            seen.add(category)
    return ordered


def split_searxng_category_batches(params: dict) -> list[dict]:
    categories = clean_string_list(str(params.get("categories") or "").split(","))
    if len(categories) <= SEARXNG_CATEGORY_BATCH_SIZE:
        return [dict(params)]

    batches = []
    ordered_categories = prioritize_searxng_categories(categories)
    for index in range(0, len(ordered_categories), SEARXNG_CATEGORY_BATCH_SIZE):
        batch_params = dict(params)
        batch_params["categories"] = ",".join(
            ordered_categories[index : index + SEARXNG_CATEGORY_BATCH_SIZE]
        )
        batches.append(batch_params)
    return batches


def split_searxng_batches(params: dict) -> list[list[dict]]:
    """Split into groups of batches, one group per category batch.

    All batches within a group (one per selected language) are executed
    before the result-count early-stop is checked, so every selected
    language gets a chance to contribute results for a given category batch.
    """
    languages = params.get("languages") or []
    base_params = {key: value for key, value in params.items() if key != "languages"}
    category_batches = split_searxng_category_batches(base_params)

    if not languages:
        return [[batch] for batch in category_batches]

    return [
        [{**category_batch, "language": language} for language in languages]
        for category_batch in category_batches
    ]


def merge_searxng_responses(
    client: SearxNGClient,
    params: dict,
    *,
    max_results: int | None = None,
    include_domains=None,
    exclude_domains=None,
    batch_timeout_s: float | None = None,
) -> dict:
    results = []
    seen_urls = set()
    suggestions = []
    answers = []
    corrections = []
    infoboxes = []
    unresponsive_engines = []
    warnings = []
    executed_params = []
    attempted_request_count = 0
    number_of_results = None
    groups = split_searxng_batches(params)
    total_batches = sum(len(group) for group in groups)

    for group in groups:
        for batch_params in group:
            executed_params.append(dict(batch_params))
            attempted_request_count += 1
            try:
                response = client.search(batch_params, timeout_s=batch_timeout_s)
            except httpx.HTTPError as exc:
                warnings.append(
                    {
                        "params": dict(batch_params),
                        "error": str(exc),
                    }
                )
                continue

            if total_batches == 1:
                number_of_results = response.get("number_of_results")

            suggestions.extend(clean_string_list(response.get("suggestions") or []))
            answers.extend(clean_string_list(response.get("answers") or []))
            corrections.extend(clean_string_list(response.get("corrections") or []))
            infoboxes.extend(response.get("infoboxes") or [])
            unresponsive_engines.extend(
                clean_string_list(response.get("unresponsive_engines") or [])
            )

            for item in response.get("results", []):
                url = str(item.get("url") or "").strip()
                if not url:
                    continue

                normalized = normalize_url(url)
                if normalized in seen_urls:
                    continue

                domain = extract_domain(url)
                if not domain_allowed(domain, include_domains or [], exclude_domains or []):
                    continue

                seen_urls.add(normalized)
                results.append(item)
                if max_results and len(results) >= max_results:
                    break

        if max_results and len(results) >= max_results:
            break

    if attempted_request_count and not results and len(warnings) == attempted_request_count:
        raise httpx.ReadTimeout("SearxNG search timed out across all category batches.")

    return {
        "results": results,
        "suggestions": clean_string_list(suggestions),
        "answers": clean_string_list(answers),
        "corrections": clean_string_list(corrections),
        "infoboxes": infoboxes,
        "unresponsive_engines": clean_string_list(unresponsive_engines),
        "warnings": warnings,
        "request_count": attempted_request_count,
        "number_of_results": number_of_results,
        "executed_params": executed_params,
    }


def build_searxng_params(topic: SearchTopic, source_scope: SourceScope, query: str) -> dict:
    params = {
        "q": query,
        "format": "json",
        "pageno": 1,
        "safesearch": source_scope.safe_search,
    }
    categories = resolve_searxng_categories(
        source_scope.searxng_categories,
        getattr(source_scope, "use_all_categories", True),
    )
    engines = normalize_searxng_engines(source_scope.searxng_engines)
    if categories:
        params["categories"] = ",".join(categories)
    if not getattr(source_scope, "use_all_engines", True) and engines:
        params["engines"] = ",".join(engines)
    languages = normalize_searxng_languages(source_scope.languages)
    if languages:
        params["languages"] = languages
    time_range = resolve_time_range(topic.lookback_days, source_scope)
    if time_range:
        params["time_range"] = time_range
    return params
