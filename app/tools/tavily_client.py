"""Tavily API client wrapper with timeout, retries, credit tracking, and error handling."""

import logging
from typing import Optional
from tavily import TavilyClient
from app.config import settings
from app.db.queries import record_api_usage, get_daily_tavily_credits

logger = logging.getLogger(__name__)


class TavilyWrapper:
    """Thin wrapper around TavilyClient with credit control and error handling."""

    def __init__(self) -> None:
        self._client: Optional[TavilyClient] = None
        if settings.TAVILY_API_KEY:
            self._client = TavilyClient(api_key=settings.TAVILY_API_KEY)

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    async def check_credit_budget(self) -> tuple[bool, int]:
        """Check if daily credit cap allows more calls.
        Returns (can_proceed, credits_used_today).
        """
        used = await get_daily_tavily_credits()
        return used < settings.DAILY_TAVILY_CREDIT_CAP, used

    async def search(
        self,
        query: str,
        include_domains: list[str] | None = None,
        max_results: int = 8,
        search_depth: str = "basic",
        ip_address: str | None = None,
    ) -> dict:
        """Perform a Tavily search with credit tracking."""
        if not self.is_configured:
            return {
                "error": "Web search is not configured. Set TAVILY_API_KEY to enable property search.",
                "results": [],
            }

        can_proceed, used = await self.check_credit_budget()
        if not can_proceed:
            return {
                "error": f"Daily search limit reached ({used}/{settings.DAILY_TAVILY_CREDIT_CAP} credits used). Try again tomorrow.",
                "results": [],
            }

        try:
            result = self._client.search(
                query=query,
                include_domains=include_domains or [],
                max_results=max_results,
                search_depth=search_depth,
                include_raw_content=True,
            )
            credits = 1 if search_depth == "basic" else 2
            await record_api_usage("tavily", "search", credits, ip_address)
            return result
        except Exception as e:
            logger.error("Tavily search failed: %s", str(e))
            return {
                "error": f"Search service temporarily unavailable. Please try again.",
                "results": [],
            }

    async def extract(
        self,
        urls: list[str],
        ip_address: str | None = None,
    ) -> dict:
        """Extract content from URLs with credit tracking."""
        if not self.is_configured:
            return {"error": "Web search is not configured.", "results": []}

        can_proceed, used = await self.check_credit_budget()
        if not can_proceed:
            return {"error": "Daily search limit reached.", "results": []}

        try:
            result = self._client.extract(urls=urls[:5])
            await record_api_usage("tavily", "extract", 1, ip_address)
            return result
        except Exception as e:
            logger.error("Tavily extract failed: %s", str(e))
            return {"error": "Content extraction temporarily unavailable.", "results": []}


tavily_wrapper = TavilyWrapper()
