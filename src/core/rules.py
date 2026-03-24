from __future__ import annotations

from dataclasses import dataclass

from src.core.enums import GameFormat, HeroClass, Rarity
from src.core.models import CardData, DeckData

DECK_SIZE = 30
MAX_COPIES_NORMAL = 2
MAX_COPIES_LEGENDARY = 1


@dataclass
class DeckValidationError:
    message: str

    def __str__(self) -> str:
        return self.message


def validate_deck(deck: DeckData, card_db: dict[str, CardData]) -> list[DeckValidationError]:
    errors: list[DeckValidationError] = []

    total = deck.total_cards
    if total != DECK_SIZE:
        errors.append(DeckValidationError(
            message=f"Deck must have exactly {DECK_SIZE} cards, got {total}"
        ))

    for card_id, count in deck.cards.items():
        card = card_db.get(card_id)
        if card is None:
            errors.append(DeckValidationError(
                message=f"Card not found: {card_id}"
            ))
            continue

        max_copies = MAX_COPIES_LEGENDARY if card.rarity == Rarity.LEGENDARY else MAX_COPIES_NORMAL
        if count > max_copies:
            errors.append(DeckValidationError(
                message=f"Legendary card '{card.name}' can only have {MAX_COPIES_LEGENDARY} copy"
            ))

        if card.hero_class not in (HeroClass.NEUTRAL, deck.hero_class):
            errors.append(DeckValidationError(
                message=f"Card '{card.name}' is {card.hero_class.value} class, "
                f"not allowed in {deck.hero_class.value} deck"
            ))

        if deck.format == GameFormat.STANDARD and not card.is_standard:
            errors.append(DeckValidationError(
                message=f"Card '{card.name}' is not in Standard format"
            ))

    return errors
