from __future__ import annotations

from django.utils import timezone

from .ai_client import AIUnavailable, call_swissai_chat, extract_json
from .models import SearchResult
from .result_locations import build_location_signature

MAX_RESULTS_PER_BATCH = 15
MAX_CONTENT_EXCERPT = 2500
MAX_SNIPPET_EXCERPT = 400

SYSTEM_PROMPT = (
    "You write short, neutral summaries of web search results collected for a monitored topic. "
    "You will be given a list of results, each with an id, a title, and a text excerpt. For each "
    "result, write one concise 1-2 sentence summary of what the page actually says, in the same "
    "language as the source text - do not invent facts not present in the excerpt.\n\n"
    'Respond with ONLY a JSON array, no prose, no markdown fences. Each element must have exactly '
    'these keys: "id" (the integer id from the input) and "summary" (the plain-text summary). '
    "Include an entry for every result you were given."
)


def _format_result_block(result: SearchResult) -> str:
    snippet = (result.snippet or "").strip()[:MAX_SNIPPET_EXCERPT]
    content_excerpt = (result.content or "").strip()[:MAX_CONTENT_EXCERPT]
    lines = [
        f"id: {result.id}",
        f"title: {result.title}",
        f"excerpt: {content_excerpt or snippet or 'unknown'}",
    ]
    return "\n".join(lines)


def _chunked(items: list, size: int):
    for index in range(0, len(items), size):
        yield items[index : index + size]


def generate_summaries_for_results(results: list[SearchResult]) -> int:
    """Generate AI summaries for the given results, batching calls and skipping unchanged content.

    Returns the number of results actually (re)summarized. Silently skips results that have
    neither content nor a snippet - there's nothing to summarize yet.
    """
    pending = []
    for result in results:
        if not (result.content or result.snippet):
            continue
        signature = build_location_signature(result)
        if signature and signature == result.summary_signature and result.ai_summary:
            continue
        pending.append((result, signature))

    if not pending:
        return 0

    summarized_count = 0
    for batch in _chunked(pending, MAX_RESULTS_PER_BATCH):
        batch_results = [result for result, _signature in batch]
        results_by_id = {result.id: result for result in batch_results}
        blocks = "\n---\n".join(_format_result_block(result) for result in batch_results)

        try:
            raw_content = call_swissai_chat(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Search results:\n{blocks}"},
                ],
                max_tokens=2000,
            )
            parsed = extract_json(raw_content, expect=list)
        except AIUnavailable:
            continue

        to_update = []
        signatures_by_id = {result.id: signature for result, signature in batch}
        for item in parsed:
            if not isinstance(item, dict):
                continue
            result_id = item.get("id")
            summary = str(item.get("summary") or "").strip()
            if not isinstance(result_id, int) or not summary or result_id not in results_by_id:
                continue
            result = results_by_id[result_id]
            result.ai_summary = summary
            result.summary_signature = signatures_by_id[result_id]
            result.updated_at = timezone.now()
            to_update.append(result)

        if to_update:
            SearchResult.objects.bulk_update(to_update, ["ai_summary", "summary_signature", "updated_at"])
            summarized_count += len(to_update)

    return summarized_count
