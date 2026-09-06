from __future__ import annotations

from django.conf import settings
from django.utils import timezone

from ..models import PushSubscription, SearchProviderConfig, SearchResult, SearchRun, SearchTopic, SourceScope
from ..result_locations import refresh_result_locations
from .crawl import Crawl4AIExtractor
from .query import (
    build_search_query,
    clean_string_list,
    domain_allowed,
    extract_domain,
    normalize_result_order,
    normalize_url,
    searxng_result_published_at,
    searxng_result_snippet,
    sort_search_items,
)
from .searxng_client import SearxNGClient, build_searxng_params, merge_searxng_responses


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

    result.image_url = payload.get("image_url") or result.image_url or result.favicon_url
    result.raw_result = raw_result
    result.save(update_fields=["content", "snippet", "image_url", "raw_result", "updated_at"])
    refresh_result_locations(result)


def run_topic_search(topic: SearchTopic, run_id: int | None = None) -> SearchRun:
    topic = SearchTopic.objects.prefetch_related("source_scopes").get(pk=topic.pk)
    source_scopes = list(topic.source_scopes.filter(enabled=True))
    if not source_scopes:
        raise ValueError(f"Topic '{topic.name}' does not have any enabled source scopes.")

    queries = [
        build_search_query(query, topic.required_terms, topic.excluded_terms, topic.category_terms)
        for query in clean_string_list(topic.queries)
    ]
    provider = SearchProviderConfig.load()
    if not provider.enabled:
        raise ValueError("SearxNG provider is disabled in provider settings.")

    client = SearxNGClient(settings.SEARXNG_BASE_URL, settings.SEARXNG_TIMEOUT_S)
    extractor = Crawl4AIExtractor()
    if run_id:
        run = SearchRun.objects.get(pk=run_id)
        run.source_scope_count = len(source_scopes)
        run.save(update_fields=["source_scope_count"])
    else:
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
        crawled_results = []
        for result_id, candidate in pending_crawls.items():
            result = SearchResult.objects.get(pk=result_id)
            pages_attempted += 1
            crawl_payload = crawl_results.get(result_id)
            if crawl_payload and crawl_payload.get("success"):
                pages_crawled += 1
            apply_crawl_content(result, crawl_payload)
            candidate["crawl_success"] = bool(crawl_payload and crawl_payload.get("success"))
            crawled_results.append(result)
        query_snapshot.append(
            {
                "crawl4ai_pages_attempted": pages_attempted,
                "crawl4ai_pages_succeeded": pages_crawled,
            }
        )

        if crawled_results:
            try:
                from ..result_summaries import generate_summaries_for_results

                generate_summaries_for_results(crawled_results)
            except Exception:  # noqa: BLE001
                pass

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


def send_push_notifications(user, topic_name: str, new_count: int) -> None:
    """Send a Web Push notification to all of a user's registered devices."""
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        return

    import json

    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        return

    subscriptions = list(PushSubscription.objects.filter(user=user))
    if not subscriptions:
        return

    label = f"new result{'s' if new_count != 1 else ''}"
    payload = json.dumps({"title": topic_name, "body": f"{new_count} {label}", "badge": new_count})

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_CLAIMS_EMAIL},
            )
        except WebPushException as exc:
            resp = getattr(exc, "response", None)
            if resp is not None and resp.status_code in (404, 410):
                sub.delete()
        except Exception:  # noqa: BLE001
            pass
