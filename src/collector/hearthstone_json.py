from __future__ import annotations
import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)


class HearthstoneJsonClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.HEARTHSTONE_JSON_URL

    async def fetch_cards(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp_ko = await client.get(f"{self.base_url}/koKR/cards.json")
            resp_ko.raise_for_status()
            raw_ko = resp_ko.json()

            resp_en = await client.get(f"{self.base_url}/enUS/cards.json")
            resp_en.raise_for_status()
            raw_en = resp_en.json()

        en_names: dict[str, str] = {}
        for card in raw_en:
            if card.get("collectible"):
                en_names[card["id"]] = card.get("name", "")

        results: list[dict] = []
        for card in raw_ko:
            if not card.get("collectible"):
                continue
            results.append({
                "card_id": card["id"],
                "dbf_id": card["dbfId"],
                "name": en_names.get(card["id"], card.get("name", "")),
                "name_ko": card.get("name", ""),
                "card_type": card.get("type", ""),
                "hero_class": card.get("cardClass", "NEUTRAL"),
                "mana_cost": card.get("cost", 0),
                "attack": card.get("attack"),
                "health": card.get("health"),
                "durability": card.get("durability"),
                "text": card.get("text", ""),
                "rarity": card.get("rarity", "FREE"),
                "set_name": card.get("set", ""),
                "mechanics": [m for m in card.get("mechanics", [])],
                "collectible": True,
                "json_data": card,
            })
        logger.info("Fetched %d collectible cards from HearthstoneJSON", len(results))
        return results
