from __future__ import annotations

import asyncio

from django.conf import settings


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
                        "image_url": "",
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

    def _extract_image_url(self, result) -> str:
        metadata = getattr(result, "metadata", {}) or {}
        if isinstance(metadata, dict):
            image = metadata.get("og:image") or metadata.get("twitter:image")
            if image:
                return str(image).strip()

        media = getattr(result, "media", {}) or {}
        images = media.get("images") if isinstance(media, dict) else None
        if images:
            first = images[0]
            if isinstance(first, dict):
                src = first.get("src") or first.get("url")
                if src:
                    return str(src).strip()
            elif isinstance(first, str) and first.strip():
                return first.strip()

        return ""

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
            "image_url": self._extract_image_url(result),
            "error": getattr(result, "error_message", "") or "",
        }
