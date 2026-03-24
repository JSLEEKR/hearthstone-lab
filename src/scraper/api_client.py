from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

HSREPLAY_BASE_URL = "https://hsreplay.net/analytics/query"
DECK_SUMMARY_URL = f"{HSREPLAY_BASE_URL}/list_decks_by_win_rate/"
DECK_DETAIL_URL = "https://hsreplay.net/api/v1/decks"


class HSReplayClient:
    def __init__(self, base_url: str = HSREPLAY_BASE_URL):
        self.base_url = base_url
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "HearthstoneDeckMaker/1.0",
        }

    async def _get(self, url: str, params: dict | None = None) -> httpx.Response:
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response

    async def fetch_deck_stats(self, format_type: str = "standard") -> list[dict]:
        game_type = "ranked_standard" if format_type == "standard" else "ranked_wild"
        params = {"GameType": game_type, "TimeRange": "LAST_7_DAYS"}
        try:
            response = await self._get(DECK_SUMMARY_URL, params=params)
            data = response.json()
            series = data.get("series", {}).get("data", {})
            all_decks = series.get("ALL", [])
            return all_decks
        except httpx.HTTPError as e:
            logger.error("HSReplay API error: %s", e)
            return []

    async def fetch_deck_detail(self, deck_id: str) -> dict[str, Any]:
        url = f"{DECK_DETAIL_URL}/{deck_id}/"
        try:
            response = await self._get(url)
            return response.json()
        except httpx.HTTPError as e:
            logger.error("HSReplay deck detail error: %s", e)
            return {}
