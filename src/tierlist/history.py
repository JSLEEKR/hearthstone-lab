from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.db.tables import TierHistory

logger = logging.getLogger(__name__)


class TierHistoryTracker:
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        deck_id: int,
        tier: str,
        sim_winrate: float | None,
        hsreplay_winrate: float | None,
        combined_winrate: float,
    ) -> TierHistory:
        entry = TierHistory(
            deck_id=deck_id,
            tier=tier,
            sim_winrate=sim_winrate,
            hsreplay_winrate=hsreplay_winrate,
            combined_winrate=combined_winrate,
        )
        self.db.add(entry)
        self.db.commit()
        return entry

    def get_history(self, deck_id: int, limit: int = 30) -> list[TierHistory]:
        return (
            self.db.query(TierHistory)
            .filter_by(deck_id=deck_id)
            .order_by(TierHistory.recorded_at.desc())
            .limit(limit)
            .all()
        )

    def get_latest_tier(self, deck_id: int) -> str | None:
        latest = (
            self.db.query(TierHistory)
            .filter_by(deck_id=deck_id)
            .order_by(TierHistory.recorded_at.desc())
            .first()
        )
        return latest.tier if latest else None
