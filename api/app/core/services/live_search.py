from __future__ import annotations

from django.conf import settings

from ..models import SearchProviderConfig, SourceScope
from .query import (
    clean_string_list,
    extract_domain,
    normalize_result_order,
    searxng_result_published_at,
    searxng_result_snippet,
    sort_search_items,
)
from .searxng_client import (
    SearxNGClient,
    merge_searxng_responses,
    normalize_searxng_engines,
    normalize_searxng_languages,
    resolve_searxng_categories,
)


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
