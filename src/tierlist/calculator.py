from __future__ import annotations

import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db.tables import Deck, HSReplayStats, Simulation

logger = logging.getLogger(__name__)


class TierCalculator:
    def __init__(self, weight_sim: float = 0.5, weight_hsreplay: float = 0.5):
        self.weight_sim = weight_sim
        self.weight_hsreplay = weight_hsreplay

    def combined_winrate(
        self, sim_winrate: float | None, hsreplay_winrate: float | None
    ) -> float | None:
        if sim_winrate is not None and hsreplay_winrate is not None:
            return (sim_winrate * self.weight_sim) + (hsreplay_winrate * self.weight_hsreplay)
        if sim_winrate is not None:
            return sim_winrate
        if hsreplay_winrate is not None:
            return hsreplay_winrate
        return None

    def get_sim_winrate(self, db: Session, deck_id: int) -> float | None:
        wins = db.query(func.count(Simulation.id)).filter(
            Simulation.winner_id == deck_id
        ).scalar()
        total = db.query(func.count(Simulation.id)).filter(
            (Simulation.deck_a_id == deck_id) | (Simulation.deck_b_id == deck_id)
        ).scalar()
        if total == 0:
            return None
        return (wins / total) * 100

    def get_hsreplay_winrate(self, db: Session, deck_id: int) -> float | None:
        latest = (
            db.query(HSReplayStats)
            .filter_by(deck_id=deck_id)
            .order_by(HSReplayStats.collected_at.desc())
            .first()
        )
        if not latest:
            return None
        return latest.winrate

    def get_deck_winrates(
        self, db: Session, format_type: str = "standard", min_games: int = 0
    ) -> list[dict]:
        decks = db.query(Deck).filter_by(format=format_type).all()
        results = []
        for deck in decks:
            sim_wr = self.get_sim_winrate(db, deck.id)
            hs_wr = self.get_hsreplay_winrate(db, deck.id)
            combined = self.combined_winrate(sim_wr, hs_wr)
            if combined is None:
                continue
            results.append({
                "deck_id": deck.id,
                "deck_name": deck.name,
                "hero_class": deck.hero_class,
                "sim_winrate": sim_wr,
                "hsreplay_winrate": hs_wr,
                "combined_winrate": combined,
            })
        results.sort(key=lambda x: x["combined_winrate"], reverse=True)
        return results
