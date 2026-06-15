from __future__ import annotations

import asyncio
from collections.abc import Iterable
from datetime import datetime, time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from .models import (
    SearchProviderConfig,
    SearchResult,
    SearchRun,
    SearchTopic,
    SourceScope,
)
from .result_locations import refresh_result_locations


def clean_string_list(values):
    cleaned = []
    for value in values or []:
        text = str(value).strip()
        if text:
            cleaned.append(text)
    return cleaned


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


def maybe_quote(term: str) -> str:
    if " " in term and not (term.startswith('"') and term.endswith('"')):
        return f'"{term}"'
    return term


def build_search_query(base_query: str, required_terms=None, excluded_terms=None) -> str:
    required_terms = clean_string_list(required_terms)
    excluded_terms = clean_string_list(excluded_terms)
    parts = [base_query.strip()]
    parts.extend(maybe_quote(term) for term in required_terms)
    parts.extend(
        f"-{maybe_quote(term)}" if not term.startswith("-") else term
        for term in excluded_terms
    )
    return " ".join(part for part in parts if part)


def normalize_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"
    clean_query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
        ],
        doseq=True,
    )
    return urlunsplit((scheme, netloc, path, clean_query, ""))


def extract_domain(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.")


def parse_result_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            return timezone.make_aware(value, timezone.get_current_timezone())
        return value
    if not isinstance(value, str):
        return None
    parsed_dt = parse_datetime(value)
    if parsed_dt:
        if timezone.is_naive(parsed_dt):
            return timezone.make_aware(parsed_dt, timezone.get_current_timezone())
        return parsed_dt
    parsed_date = parse_date(value)
    if parsed_date:
        return timezone.make_aware(
            datetime.combine(parsed_date, time.min),
            timezone.get_current_timezone(),
        )
    return None


def normalize_domain_rule(value: str) -> str:
    return value.strip().lower().removeprefix("www.")


def domain_matches_rule(domain: str, rule: str) -> bool:
    normalized_rule = normalize_domain_rule(rule)
    return domain == normalized_rule or domain.endswith(f".{normalized_rule}")


def domain_allowed(domain: str, include_domains: Iterable[str], exclude_domains: Iterable[str]) -> bool:
    include_rules = clean_string_list(include_domains)
    exclude_rules = clean_string_list(exclude_domains)
    if include_rules and not any(domain_matches_rule(domain, rule) for rule in include_rules):
        return False
    if exclude_rules and any(domain_matches_rule(domain, rule) for rule in exclude_rules):
        return False
    return True


def resolve_time_range(lookback_days: int, source_scope: SourceScope) -> str | None:
    if source_scope.time_range == SourceScope.TimeRange.ANY:
        return None
    if source_scope.time_range != SourceScope.TimeRange.AUTO:
        return source_scope.time_range
    if lookback_days <= 1:
        return SourceScope.TimeRange.DAY
    if lookback_days <= 31:
        return SourceScope.TimeRange.MONTH
    return SourceScope.TimeRange.YEAR


def searxng_result_snippet(item: dict) -> str:
    return (
        item.get("content")
        or item.get("snippet")
        or item.get("description")
        or item.get("text")
        or ""
    )


def searxng_result_published_at(item: dict):
    return parse_result_datetime(
        item.get("publishedDate")
        or item.get("published_date")
        or item.get("publishedAt")
        or item.get("published_at")
        or item.get("date")
    )


def searxng_result_score(item: dict) -> float | None:
    score = item.get("score")
    try:
        return float(score)
    except (TypeError, ValueError):
        return None


def searxng_result_timestamp(item: dict) -> float | None:
    published_at = searxng_result_published_at(item)
    if not published_at:
        return None
    return published_at.timestamp()


def normalize_result_order(value: str | None) -> str:
    if value == SourceScope.ResultOrder.NEWEST:
        return SourceScope.ResultOrder.NEWEST
    return SourceScope.ResultOrder.RELEVANCE


def sort_search_items(items: list[dict], result_order: str, max_results: int | None = None) -> list[dict]:
    normalized_order = normalize_result_order(result_order)
    indexed_items = list(enumerate(items))

    if normalized_order == SourceScope.ResultOrder.NEWEST:
        indexed_items.sort(
            key=lambda pair: (
                searxng_result_timestamp(pair[1]) is not None,
                searxng_result_timestamp(pair[1]) or float("-inf"),
                searxng_result_score(pair[1]) is not None,
                searxng_result_score(pair[1]) or float("-inf"),
                -pair[0],
            ),
            reverse=True,
        )
    else:
        if any(searxng_result_score(item) is not None for item in items):
            indexed_items.sort(
                key=lambda pair: (
                    searxng_result_score(pair[1]) is not None,
                    searxng_result_score(pair[1]) or float("-inf"),
                    -pair[0],
                ),
                reverse=True,
            )

    ordered_items = [item for _, item in indexed_items]
    if max_results:
        return ordered_items[:max_results]
    return ordered_items


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


class Crawl4AIExtractor:
    def __init__(self):
        self.enabled = bool(getattr(settings, "CRAWL4AI_ENABLED", True))
        self.max_pages_per_run = int(getattr(settings, "CRAWL4AI_MAX_PAGES_PER_RUN", 25))

    async def _crawl_many(self, candidates: list[dict]) -> dict[int, dict]:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
        from crawl4ai.content_filter_strategy import PruningContentFilter
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

        browser_config = BrowserConfig(
            browser_type="chromium",
            headless=getattr(settings, "CRAWL4AI_HEADLESS", True),
            verbose=False,
        )
        markdown_generator = DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(
                threshold=getattr(settings, "CRAWL4AI_PRUNE_THRESHOLD", 0.4),
                threshold_type="fixed",
            )
        )
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            markdown_generator=markdown_generator,
            word_count_threshold=getattr(settings, "CRAWL4AI_WORD_COUNT_THRESHOLD", 20),
            exclude_external_images=True,
            exclude_social_media_links=True,
            remove_overlay_elements=True,
        )

        extracted = {}
        async with AsyncWebCrawler(config=browser_config) as crawler:
            for candidate in candidates:
                try:
                    result = await crawler.arun(url=candidate["url"], config=run_config)
                    extracted[candidate["result_id"]] = self._serialize_result(result)
                except Exception as exc:
                    extracted[candidate["result_id"]] = {
                        "success": False,
                        "content": "",
                        "references": "",
                        "error": str(exc),
                    }
        return extracted

    def extract_many(self, candidates: list[dict]) -> dict[int, dict]:
        if not self.enabled or not candidates:
            return {}
        trimmed = candidates[: self.max_pages_per_run]
        return self._run_async(self._crawl_many(trimmed))

    def _run_async(self, coroutine):
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop and running_loop.is_running():
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coroutine)
            finally:
                loop.close()
        return asyncio.run(coroutine)

    def _serialize_result(self, result) -> dict:
        markdown = getattr(result, "markdown", None)
        if isinstance(markdown, str):
            raw_markdown = markdown
            fit_markdown = ""
            references = ""
        else:
            raw_markdown = getattr(markdown, "raw_markdown", "") or ""
            fit_markdown = getattr(markdown, "fit_markdown", "") or ""
            references = getattr(markdown, "references_markdown", "") or ""

        content = (fit_markdown or raw_markdown or "").strip()
        metadata = getattr(result, "metadata", {}) or {}

        return {
            "success": bool(getattr(result, "success", False)),
            "content": content[:40000],
            "references": references[:12000],
            "title": metadata.get("title") if isinstance(metadata, dict) else "",
            "error": getattr(result, "error_message", "") or "",
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


def stringify_searxng_param(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (list, tuple)):
        items = clean_string_list(value)
        return ",".join(items) if items else None
    text = str(value).strip()
    return text or None


def build_direct_searxng_params(payload: dict) -> dict:
    params = {
        "q": payload["q"],
        "format": "json",
        "pageno": payload.get("pageno") or 1,
        "safesearch": payload.get("safesearch", 0),
    }
    categories = resolve_searxng_categories(
        payload.get("categories"),
        payload.get("use_all_categories", True),
    )
    use_all_engines = payload.get("use_all_engines", True)
    engines = normalize_searxng_engines(payload.get("engines"))

    if categories:
        params["categories"] = ",".join(categories)
    if not use_all_engines and engines:
        params["engines"] = ",".join(engines)
    languages = normalize_searxng_languages(payload.get("languages"))
    if languages:
        params["languages"] = languages
    if payload.get("time_range"):
        params["time_range"] = payload["time_range"]

    for key, raw_value in (payload.get("extra_params") or {}).items():
        clean_key = str(key).strip()
        if not clean_key or clean_key in params or clean_key == "format":
            continue
        clean_value = stringify_searxng_param(raw_value)
        if clean_value is not None:
            params[clean_key] = clean_value

    return params


def run_direct_searxng_search(payload: dict) -> dict:
    provider = SearchProviderConfig.load()
    if not provider.enabled:
        raise ValueError("SearxNG provider is disabled in provider settings.")

    client = SearxNGClient(settings.SEARXNG_BASE_URL, settings.SEARXNG_TIMEOUT_S)
    params = build_direct_searxng_params(payload)
    include_domains = payload.get("include_domains") or []
    exclude_domains = payload.get("exclude_domains") or []
    max_results = int(payload.get("max_results") or 10)
    result_order = normalize_result_order(payload.get("result_order"))
    search_payload = merge_searxng_responses(
        client,
        params,
        max_results=None if result_order == SourceScope.ResultOrder.NEWEST else max_results,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        batch_timeout_s=min(settings.SEARXNG_TIMEOUT_S, 12.0),
    )

    results = []
    ordered_items = sort_search_items(search_payload.get("results", []), result_order, max_results)
    for item in ordered_items:
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        domain = extract_domain(url)

        results.append(
            {
                "position": len(results) + 1,
                "title": (item.get("title") or url)[:500],
                "url": url,
                "domain": domain,
                "snippet": searxng_result_snippet(item)[:1200],
                "engine": str(item.get("engine") or ""),
                "engines": clean_string_list(item.get("engines") or []),
                "published_at": searxng_result_published_at(item),
                "score": item.get("score"),
                "category": str(item.get("category") or ""),
                "thumbnail": item.get("thumbnail") or item.get("img_src") or "",
                "raw_result": dict(item),
            }
        )
        if len(results) >= max_results:
            break

    return {
        "query": payload["q"],
        "params": params,
        "result_order": result_order,
        "executed_params": search_payload["executed_params"],
        "request_count": search_payload["request_count"],
        "result_count": len(results),
        "number_of_results": search_payload.get("number_of_results"),
        "suggestions": search_payload["suggestions"],
        "answers": search_payload["answers"],
        "corrections": search_payload["corrections"],
        "infoboxes": search_payload["infoboxes"],
        "unresponsive_engines": search_payload["unresponsive_engines"],
        "warnings": search_payload["warnings"],
        "results": results,
    }


def upsert_search_result(
    topic: SearchTopic,
    source_scope: SourceScope,
    run: SearchRun,
    built_query: str,
    item: dict,
) -> tuple[SearchResult | None, bool, bool]:
    now = timezone.now()
    url = item.get("url", "").strip()
    if not url:
        return None, False, False

    domain = extract_domain(url)
    if not domain_allowed(domain, source_scope.include_domains, source_scope.exclude_domains):
        return None, False, False

    normalized = normalize_url(url)
    title = (item.get("title") or url)[:500]
    snippet = searxng_result_snippet(item)[:1200]
    favicon_url = item.get("thumbnail") or item.get("img_src") or ""
    score = item.get("score")
    published_at = searxng_result_published_at(item)

    result, created = SearchResult.objects.get_or_create(
        topic=topic,
        normalized_url=normalized,
        defaults={
            "source_scope": source_scope,
            "last_run": run,
            "title": title,
            "url": url,
            "domain": domain,
            "snippet": snippet,
            "content": "",
            "favicon_url": favicon_url,
            "score": score,
            "published_at": published_at,
            "matched_queries": [built_query],
            "first_seen_at": now,
            "last_seen_at": now,
            "raw_result": dict(item),
            "is_new": True,
        },
    )

    if created:
        refresh_result_locations(result)
        return result, True, True

    matched_queries = clean_string_list(result.matched_queries)
    if built_query not in matched_queries:
        matched_queries.append(built_query)

    previous_raw = result.raw_result if isinstance(result.raw_result, dict) else {}
    crawl_metadata = previous_raw.get("_crawl4ai")
    raw_result = dict(item)
    if crawl_metadata:
        raw_result["_crawl4ai"] = crawl_metadata

    result.source_scope = source_scope
    result.last_run = run
    result.title = title
    result.url = url
    result.domain = domain
    result.snippet = snippet or result.snippet
    result.favicon_url = favicon_url
    result.score = score
    result.published_at = published_at or result.published_at
    result.matched_queries = matched_queries
    result.last_seen_at = now
    result.raw_result = raw_result
    result.save()
    refresh_result_locations(result)
    return result, False, not bool(result.content)


def apply_crawl_content(result: SearchResult, crawl_payload: dict | None):
    payload = crawl_payload or {}
    raw_result = dict(result.raw_result or {})
    raw_result["_crawl4ai"] = {
        "success": payload.get("success", False),
        "error": payload.get("error", ""),
    }
    if payload.get("references"):
        raw_result["_crawl4ai"]["references_markdown"] = payload["references"]

    content = (payload.get("content") or "").strip()
    if content:
        result.content = content
        if not result.snippet:
            result.snippet = content[:1200]

    result.raw_result = raw_result
    result.save(update_fields=["content", "snippet", "raw_result", "updated_at"])
    refresh_result_locations(result)


def run_topic_search(topic: SearchTopic) -> SearchRun:
    topic = SearchTopic.objects.prefetch_related("source_scopes").get(pk=topic.pk)
    source_scopes = list(topic.source_scopes.filter(enabled=True))
    if not source_scopes:
        raise ValueError(f"Topic '{topic.name}' does not have any enabled source scopes.")

    queries = [
        build_search_query(query, topic.required_terms, topic.excluded_terms)
        for query in clean_string_list(topic.queries)
    ]
    provider = SearchProviderConfig.load()
    if not provider.enabled:
        raise ValueError("SearxNG provider is disabled in provider settings.")

    client = SearxNGClient(settings.SEARXNG_BASE_URL, settings.SEARXNG_TIMEOUT_S)
    extractor = Crawl4AIExtractor()
    run = SearchRun.objects.create(
        topic=topic,
        status=SearchRun.Status.RUNNING,
        source_scope_count=len(source_scopes),
        query_snapshot=[],
    )

    topic.last_run_status = SearchTopic.RunStatus.RUNNING
    topic.last_checked_at = timezone.now()
    topic.save(update_fields=["last_run_status", "last_checked_at", "updated_at"])

    request_count = 0
    pages_crawled = 0
    results_collected = 0
    new_results_count = 0
    query_snapshot = []
    status_value = SearchRun.Status.SUCCEEDED
    error_message = ""
    pending_crawls = {}
    had_warnings = False

    try:
        for source_scope in source_scopes:
            for built_query in queries:
                params = build_searxng_params(topic, source_scope, built_query)
                result_limit = min(topic.max_results_per_query, source_scope.max_results)
                result_order = normalize_result_order(getattr(source_scope, "result_order", None))
                search_payload = merge_searxng_responses(
                    client,
                    params,
                    max_results=None if result_order == SourceScope.ResultOrder.NEWEST else result_limit,
                    include_domains=source_scope.include_domains,
                    exclude_domains=source_scope.exclude_domains,
                    batch_timeout_s=min(settings.SEARXNG_TIMEOUT_S, 20.0),
                )

                request_count += search_payload["request_count"]
                accepted_results = 0
                ordered_items = sort_search_items(
                    search_payload.get("results", []),
                    result_order,
                    result_limit,
                )
                for item in ordered_items:
                    result, is_new, needs_crawl = upsert_search_result(
                        topic=topic,
                        source_scope=source_scope,
                        run=run,
                        built_query=built_query,
                        item=item,
                    )
                    if result is None:
                        continue

                    accepted_results += 1
                    results_collected += 1
                    if is_new:
                        new_results_count += 1
                    if needs_crawl and len(pending_crawls) < extractor.max_pages_per_run:
                        pending_crawls[result.id] = {
                            "result_id": result.id,
                            "url": result.url,
                        }

                query_snapshot.append(
                    {
                        "scope": source_scope.name,
                        "query": built_query,
                        "params": params,
                        "result_order": result_order,
                        "executed_params": search_payload["executed_params"],
                        "accepted_results": accepted_results,
                        "response_result_count": len(search_payload.get("results", [])),
                        "ordered_result_count": len(ordered_items),
                        "warnings": search_payload["warnings"],
                    }
                )
                if search_payload["warnings"]:
                    had_warnings = True
    except Exception as exc:
        status_value = SearchRun.Status.FAILED
        error_message = str(exc)

    if pending_crawls:
        crawl_results = extractor.extract_many(list(pending_crawls.values()))
        pages_attempted = 0
        for result_id, candidate in pending_crawls.items():
            result = SearchResult.objects.get(pk=result_id)
            pages_attempted += 1
            crawl_payload = crawl_results.get(result_id)
            if crawl_payload and crawl_payload.get("success"):
                pages_crawled += 1
            apply_crawl_content(result, crawl_payload)
            candidate["crawl_success"] = bool(crawl_payload and crawl_payload.get("success"))
        query_snapshot.append(
            {
                "crawl4ai_pages_attempted": pages_attempted,
                "crawl4ai_pages_succeeded": pages_crawled,
            }
        )

    completed_at = timezone.now()
    if status_value == SearchRun.Status.SUCCEEDED and had_warnings:
        status_value = SearchRun.Status.LIMITED
    run.status = status_value
    run.completed_at = completed_at
    run.request_count = request_count
    run.pages_crawled = pages_crawled
    run.results_collected = results_collected
    run.new_results_count = new_results_count
    run.query_snapshot = query_snapshot
    run.error_message = error_message
    run.save()

    topic.last_checked_at = completed_at
    if status_value == SearchRun.Status.SUCCEEDED:
        topic.last_success_at = completed_at
        topic.last_run_status = SearchTopic.RunStatus.SUCCEEDED
    elif status_value == SearchRun.Status.LIMITED:
        topic.last_success_at = completed_at
        topic.last_run_status = SearchTopic.RunStatus.LIMITED
    else:
        topic.last_run_status = SearchTopic.RunStatus.FAILED
    topic.set_next_run(completed_at)
    if new_results_count:
        topic.last_new_results_at = completed_at
    topic.save(
        update_fields=[
            "next_run_at",
            "last_checked_at",
            "last_success_at",
            "last_new_results_at",
            "last_run_status",
            "updated_at",
        ]
    )

    return run
