from __future__ import annotations

import logging

from config import settings

logger = logging.getLogger(__name__)


class TierRanker:
    def __init__(self, thresholds: dict | None = None):
        self.thresholds = thresholds or settings.TIER_THRESHOLDS

    def assign_tier(self, winrate: float) -> str:
        if winrate >= self.thresholds["S"]:
            return "S"
        if winrate >= self.thresholds["A"]:
            return "A"
        if winrate >= self.thresholds["B"]:
            return "B"
        if winrate >= self.thresholds["C"]:
            return "C"
        return "D"

    def rank_decks(self, deck_winrates: list[dict]) -> list[dict]:
        ranked = []
        for entry in deck_winrates:
            tier = self.assign_tier(entry["combined_winrate"])
            ranked.append({**entry, "tier": tier})
        ranked.sort(key=lambda x: x["combined_winrate"], reverse=True)
        return ranked
