from __future__ import annotations
import asyncio
import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)
MAX_RETRIES = 3
BACKOFF_BASE = 2.0


class BlizzardApiClient:
    def __init__(self, client_id: str | None = None, client_secret: str | None = None, region: str | None = None):
        self.client_id = client_id or settings.BLIZZARD_CLIENT_ID
        self.client_secret = client_secret or settings.BLIZZARD_CLIENT_SECRET
        self.region = region or settings.BLIZZARD_API_REGION
        self._access_token: str | None = None

    async def _get_access_token(self) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://oauth.battle.net/token",
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
            )
            resp.raise_for_status()
            data = await resp.json()
            self._access_token = data["access_token"]
            return self._access_token

    async def _request_with_retry(self, client: httpx.AsyncClient, url: str, params: dict) -> dict:
        for attempt in range(MAX_RETRIES):
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return await resp.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < MAX_RETRIES - 1:
                    wait = BACKOFF_BASE ** (attempt + 1)
                    logger.warning("Rate limited, retrying in %.1fs...", wait)
                    await asyncio.sleep(wait)
                elif e.response.status_code == 401 and attempt < MAX_RETRIES - 1:
                    logger.warning("Auth failed, refreshing token...")
                    await self._get_access_token()
                    params["access_token"] = self._access_token
                else:
                    raise
        return {}

    async def fetch_cards(self) -> list[dict]:
        if not self._access_token:
            await self._get_access_token()

        base_url = f"https://{self.region}.api.blizzard.com/hearthstone/cards"
        results: list[dict] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "access_token": self._access_token, "locale": "en_US",
                "pageSize": 500, "page": 1, "collectible": "1",
            }
            data = await self._request_with_retry(client, base_url, params)
            page_count = data.get("pageCount", 1)
            for card in data.get("cards", []):
                results.append(self._map_card(card))

            for page in range(2, page_count + 1):
                params["page"] = page
                data = await self._request_with_retry(client, base_url, params)
                for card in data.get("cards", []):
                    results.append(self._map_card(card))

        logger.info("Fetched %d cards from Blizzard API", len(results))
        return results

    @staticmethod
    def _map_card(card: dict) -> dict:
        return {
            "dbf_id": card.get("id"),
            "name": card.get("name", ""),
            "flavor_text": card.get("flavorText", ""),
            "raw_data": card,
        }
