"""
Solodit API Client
Fetches audit reports from the Solodit knowledge base (49,000+ findings).

API contract (verified with real key, HTTP 200):
- Endpoint: POST https://solodit.cyfrin.io/api/v1/solodit/findings
- Auth: X-Cyfrin-API-Key header (NOT Authorization Bearer)
- Body: {"page": N, "pageSize": N, "filters": {"keywords": ..., "impact": [...]}}
- Response: {"findings": [...], "metadata": {...}, "rateLimit": {...}}
- Rate limit: 20 req/60s, use rateLimit.remaining / rateLimit.reset to throttle.
"""

import os
import time
import aiohttp

from ..utils.logger import get_logger

logger = get_logger(__name__)

# Real API endpoint (can be overridden via SOLODIT_API_URL env)
DEFAULT_API_URL = "https://solodit.cyfrin.io/api/v1/solodit/findings"


class SoloditFetcher:
    """
    Client for the Solodit API (Cyfrin audit findings database).

    API key resolution: SOLODIT_API_KEY → CYFRIN_API_KEY (fallback).
    Base URL: SOLODIT_API_URL env → default https://solodit.cyfrin.io/api/v1/solodit/findings.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("SOLODIT_API_KEY") or os.getenv("CYFRIN_API_KEY")
        self.base_url = os.getenv("SOLODIT_API_URL", DEFAULT_API_URL)

    async def fetch_reports(
        self,
        keywords: str = "",
        impact: list[str] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """
        Fetch audit reports from Solodit.

        Args:
            keywords: Search keywords (e.g. "reentrancy")
            impact: Impact filter, e.g. ["HIGH", "MEDIUM"] or None for all
            page: Page number (1-indexed)
            page_size: Results per page (max 100)

        Returns:
            Dict with keys: findings (list), metadata (dict with totalResults,
            totalPages, etc.), rateLimit (dict with limit, remaining, reset).
            Returns {"findings": [], "metadata": {}, "rateLimit": {}} on error.

        Raises:
            ValueError: If api_key is not configured.
        """
        if not self.api_key:
            raise ValueError(
                "SOLODIT_API_KEY not set. Set SOLODIT_API_KEY or CYFRIN_API_KEY env var."
            )

        headers = {
            "X-Cyfrin-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

        # Build filters – only include non-empty items
        filters: dict = {}
        if keywords:
            filters["keywords"] = keywords
        if impact is not None:
            filters["impact"] = impact

        body: dict = {
            "page": page,
            "pageSize": page_size,
        }
        if filters:
            body["filters"] = filters

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, json=body, headers=headers) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        logger.warning(f"Solodit HTTP {resp.status}: {text[:200]}")
                        return {"findings": [], "metadata": {}, "rateLimit": {}}
                    data = await resp.json()
                    return data
        except Exception as e:
            logger.warning(f"Solodit fetch failed: {e}")
            return {"findings": [], "metadata": {}, "rateLimit": {}}
