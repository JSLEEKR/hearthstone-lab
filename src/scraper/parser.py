from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.db.tables import Deck, HSReplayStats

logger = logging.getLogger(__name__)


class HSReplayParser:
    def __init__(self, db: Session):
        self.db = db

    def parse_deck_stats(
        self, raw_data: list[dict], format_type: str = "standard"
    ) -> list[dict]:
        parsed = []
        for entry in raw_data:
            parsed.append({
                "deck_id": entry.get("deck_id"),
                "winrate": entry.get("win_rate", 0.0),
                "playrate": entry.get("popularity", 0.0),
                "games_played": entry.get("total_games", 0),
                "hero_class": entry.get("player_class_name", "UNKNOWN"),
                "deckstring": entry.get("deckstring"),
                "format": format_type,
            })
        return parsed

    def save_stats(
        self, deck_id: int, winrate: float, playrate: float, games_played: int
    ) -> HSReplayStats:
        stats = HSReplayStats(
            deck_id=deck_id,
            winrate=winrate,
            playrate=playrate,
            games_played=games_played,
        )
        self.db.add(stats)
        self.db.commit()
        return stats

    def find_or_create_deck(
        self, hero_class: str, format_type: str, deckstring: str | None = None,
        name: str | None = None,
    ) -> Deck:
        if deckstring:
            existing = self.db.query(Deck).filter_by(
                deckstring=deckstring, format=format_type
            ).first()
            if existing:
                return existing

        deck_name = name or f"HSReplay {hero_class}"
        deck = Deck(
            name=deck_name,
            hero_class=hero_class,
            format=format_type,
            deckstring=deckstring,
            source="hsreplay",
        )
        self.db.add(deck)
        self.db.commit()
        return deck
