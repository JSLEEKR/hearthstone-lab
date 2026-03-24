from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.db.tables import Card, Deck, DeckCard

logger = logging.getLogger(__name__)


class ManualDeckBuilder:
    def __init__(self, db: Session):
        self.db = db

    def search_cards(
        self,
        query: str | None = None,
        hero_class: str | None = None,
        mana_cost: int | None = None,
        rarity: str | None = None,
        set_name: str | None = None,
        collectible: bool = True,
    ) -> list[Card]:
        q = self.db.query(Card).filter(Card.collectible == collectible)

        if query:
            q = q.filter(Card.name.ilike(f"%{query}%") | Card.name_ko.ilike(f"%{query}%"))
        if hero_class:
            q = q.filter(Card.hero_class.in_([hero_class, "NEUTRAL"]))
        if mana_cost is not None:
            q = q.filter(Card.mana_cost == mana_cost)
        if rarity:
            q = q.filter(Card.rarity == rarity)
        if set_name:
            q = q.filter(Card.set_name == set_name)

        return q.order_by(Card.mana_cost, Card.name).all()

    def create_deck(self, name: str, hero_class: str, format: str) -> Deck:
        deck = Deck(name=name, hero_class=hero_class, format=format, source="manual")
        self.db.add(deck)
        self.db.commit()
        return deck

    def add_card(self, deck_id: int, card_id: str) -> bool:
        card = self.db.query(Card).filter_by(card_id=card_id).first()
        if not card:
            return False

        existing = self.db.query(DeckCard).filter_by(
            deck_id=deck_id, card_id=card.id
        ).first()

        if existing:
            max_count = 1 if card.rarity == "LEGENDARY" else 2
            if existing.count >= max_count:
                return False
            existing.count += 1
        else:
            dc = DeckCard(deck_id=deck_id, card_id=card.id, count=1)
            self.db.add(dc)

        self.db.commit()
        return True

    def remove_card(self, deck_id: int, card_id: str) -> bool:
        card = self.db.query(Card).filter_by(card_id=card_id).first()
        if not card:
            return False

        existing = self.db.query(DeckCard).filter_by(
            deck_id=deck_id, card_id=card.id
        ).first()

        if not existing:
            return False

        if existing.count > 1:
            existing.count -= 1
        else:
            self.db.delete(existing)

        self.db.commit()
        return True

    def get_deck_cards(self, deck_id: int) -> list[dict]:
        results = (
            self.db.query(DeckCard, Card)
            .join(Card, DeckCard.card_id == Card.id)
            .filter(DeckCard.deck_id == deck_id)
            .order_by(Card.mana_cost, Card.name)
            .all()
        )
        return [
            {
                "card_id": card.card_id,
                "name": card.name,
                "name_ko": card.name_ko,
                "mana_cost": card.mana_cost,
                "count": dc.count,
                "rarity": card.rarity,
                "card_type": card.card_type,
            }
            for dc, card in results
        ]
