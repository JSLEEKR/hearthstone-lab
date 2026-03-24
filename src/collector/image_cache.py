from __future__ import annotations
import asyncio
import logging
from pathlib import Path
import httpx
from config import settings

logger = logging.getLogger(__name__)


class ImageCacheManager:
    def __init__(self, cache_dir: Path | None = None, base_url: str | None = None):
        self.cache_dir = Path(cache_dir or settings.IMAGE_CACHE_DIR)
        self.base_url = base_url or settings.IMAGE_BASE_URL
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, card_id: str) -> Path:
        return self.cache_dir / f"{card_id}.png"

    async def get_card_image(self, card_id: str) -> Path | None:
        cached = self._cache_path(card_id)
        if cached.exists():
            return cached

        url = f"{self.base_url}/{card_id}.png"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                cached.write_bytes(resp.content)
                return cached
        except httpx.HTTPStatusError:
            logger.warning("Failed to download image for %s", card_id)
            return None
        except httpx.RequestError:
            logger.warning("Network error downloading image for %s", card_id)
            return None

    async def bulk_download(self, card_ids: list[str], concurrency: int = 10) -> dict[str, Path]:
        semaphore = asyncio.Semaphore(concurrency)
        results: dict[str, Path] = {}

        async def _download(cid: str):
            async with semaphore:
                path = await self.get_card_image(cid)
                if path:
                    results[cid] = path

        await asyncio.gather(*[_download(cid) for cid in card_ids])
        logger.info("Downloaded %d/%d card images", len(results), len(card_ids))
        return results
