from __future__ import annotations

import json
import re

import httpx
from django.conf import settings

_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


class AIUnavailable(RuntimeError):
    pass


def call_swissai_chat(messages: list[dict], *, max_tokens: int = 3000, temperature: float = 0.1) -> str:
    api_key = settings.SWISSAI_API_KEY
    if not api_key:
        raise AIUnavailable("SwissAI API key is not configured.")

    try:
        response = httpx.post(
            f"{settings.SWISSAI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.SWISSAI_MODEL,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=settings.SWISSAI_TIMEOUT_S,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise AIUnavailable("SwissAI request failed.") from exc

    payload = response.json()
    try:
        return payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIUnavailable("SwissAI returned an unexpected response.") from exc


def extract_json(text: str, *, expect: type = list):
    """Parse a JSON array/object out of an LLM response, tolerating code fences and stray prose."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        pattern = _JSON_ARRAY_RE if expect is list else _JSON_OBJECT_RE
        match = pattern.search(cleaned)
        if not match:
            raise AIUnavailable("AI response was not valid JSON.")
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            # The greedy regex can span past the first JSON value (e.g. the model
            # repeated itself or added trailing prose) - fall back to parsing just
            # the first valid JSON value and ignore whatever follows it.
            try:
                parsed, _end = json.JSONDecoder().raw_decode(match.group(0))
            except json.JSONDecodeError as exc:
                raise AIUnavailable("AI response was not valid JSON.") from exc

    if expect is list and isinstance(parsed, dict):
        # Models often collapse a single-item array into a bare object - tolerate it.
        parsed = [parsed]

    if not isinstance(parsed, expect):
        raise AIUnavailable(f"AI response was not a JSON {expect.__name__}.")
    return parsed
