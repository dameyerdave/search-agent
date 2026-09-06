from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from ..models import SourceScope


def clean_string_list(values):
    cleaned = []
    for value in values or []:
        text = str(value).strip()
        if text:
            cleaned.append(text)
    return cleaned


def maybe_quote(term: str) -> str:
    if " " in term and not (term.startswith('"') and term.endswith('"')):
        return f'"{term}"'
    return term


def build_search_query(
    base_query: str,
    required_terms=None,
    excluded_terms=None,
    category_terms=None,
) -> str:
    required_terms = clean_string_list(required_terms)
    excluded_terms = clean_string_list(excluded_terms)
    parts = [base_query.strip()]
    parts.extend(maybe_quote(term) for term in required_terms)

    for terms in (category_terms or {}).values():
        cleaned = clean_string_list(terms)
        if not cleaned:
            continue
        if len(cleaned) == 1:
            parts.append(maybe_quote(cleaned[0]))
        else:
            parts.append(f"({' OR '.join(maybe_quote(term) for term in cleaned)})")

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
