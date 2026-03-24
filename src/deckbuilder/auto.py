from __future__ import annotations

import logging
import random

from sqlalchemy.orm import Session

from src.db.tables import Card
from src.deckbuilder.archetypes import classify_from_cards

logger = logging.getLogger(__name__)

DECK_SIZE = 30

CURVE_TARGETS = {
    "aggro":    {1: 6, 2: 8, 3: 6, 4: 4, 5: 2, 6: 2, 7: 1, 8: 1},
    "midrange": {1: 3, 2: 5, 3: 6, 4: 6, 5: 4, 6: 3, 7: 2, 8: 1},
    "control":  {1: 2, 2: 4, 3: 4, 4: 4, 5: 4, 6: 4, 7: 4, 8: 4},
}


class AutoDeckBuilder:
    def __init__(self, db: Session):
        self.db = db

    def generate_deck(
        self,
        hero_class: str,
        format: str = "standard",
        archetype: str | None = None,
    ) -> dict:
        q = self.db.query(Card).filter(
            Card.collectible == True,
            Card.hero_class.in_([hero_class, "NEUTRAL"]),
        )
        if format == "standard":
            q = q.filter(Card.is_standard == True)

        available = q.all()

        if not archetype:
            archetype = "midrange"

        curve = CURVE_TARGETS.get(archetype, CURVE_TARGETS["midrange"])

        deck_cards: dict[int, dict] = {}
        total = 0

        by_cost: dict[int, list[Card]] = {}
        for card in available:
            cost = min(card.mana_cost, 8)
            if cost not in by_cost:
                by_cost[cost] = []
            by_cost[cost].append(card)

        for cost in sorted(curve.keys()):
            target = curve[cost]
            pool = by_cost.get(cost, [])
            if not pool:
                continue

            class_cards = [c for c in pool if c.hero_class == hero_class]
            neutral_cards = [c for c in pool if c.hero_class == "NEUTRAL"]

            scored = []
            for c in class_cards:
                scored.append((c, self._score_card(c, archetype) + 5))
            for c in neutral_cards:
                scored.append((c, self._score_card(c, archetype)))

            scored.sort(key=lambda x: x[1], reverse=True)

            added_at_cost = 0
            for card, score in scored:
                if total >= DECK_SIZE or added_at_cost >= target:
                    break

                max_copies = 1 if card.rarity == "LEGENDARY" else 2
                current = deck_cards.get(card.id, {}).get("count", 0)
                copies_to_add = min(max_copies - current, target - added_at_cost, DECK_SIZE - total)

                if copies_to_add > 0:
                    if card.id not in deck_cards:
                        deck_cards[card.id] = {
                            "card_id": card.card_id,
                            "name": card.name,
                            "name_ko": card.name_ko,
                            "mana_cost": card.mana_cost,
                            "rarity": card.rarity,
                            "card_type": card.card_type,
                            "count": copies_to_add,
                        }
                    else:
                        deck_cards[card.id]["count"] += copies_to_add

                    total += copies_to_add
                    added_at_cost += copies_to_add

        if total < DECK_SIZE:
            remaining = [c for c in available if c.id not in deck_cards]
            random.shuffle(remaining)
            for card in remaining:
                if total >= DECK_SIZE:
                    break
                max_copies = 1 if card.rarity == "LEGENDARY" else 2
                copies = min(max_copies, DECK_SIZE - total)
                deck_cards[card.id] = {
                    "card_id": card.card_id,
                    "name": card.name,
                    "name_ko": card.name_ko,
                    "mana_cost": card.mana_cost,
                    "rarity": card.rarity,
                    "card_type": card.card_type,
                    "count": copies,
                }
                total += copies

        cards_list = list(deck_cards.values())
        detected_archetype = classify_from_cards(cards_list)

        return {
            "hero_class": hero_class,
            "format": format,
            "archetype": detected_archetype,
            "cards": cards_list,
        }

    @staticmethod
    def _score_card(card: Card, archetype: str) -> float:
        score = 0.0
        if card.card_type == "MINION":
            attack = card.attack or 0
            health = card.health or 0
            cost = max(card.mana_cost, 1)
            score = (attack + health) / cost

            if archetype == "aggro":
                score += attack / cost
            elif archetype == "control":
                score += health / cost
        elif card.card_type == "SPELL":
            score = 3.0 / max(card.mana_cost, 1)
        return score
