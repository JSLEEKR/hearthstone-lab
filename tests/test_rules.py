import pytest
from src.core.enums import CardType, Rarity, HeroClass, GameFormat
from src.core.models import CardData, DeckData
from src.core.rules import validate_deck, DeckValidationError


def _card(card_id: str, hero_class: HeroClass = HeroClass.NEUTRAL,
          rarity: Rarity = Rarity.COMMON, is_standard: bool = True) -> CardData:
    return CardData(
        card_id=card_id, dbf_id=hash(card_id) % 10000, name=card_id,
        name_ko=card_id, card_type=CardType.MINION, hero_class=hero_class,
        mana_cost=1, attack=1, health=1, rarity=rarity, set_name="TEST",
        collectible=True, is_standard=is_standard,
    )


def _card_db(cards: list[CardData]) -> dict[str, CardData]:
    return {c.card_id: c for c in cards}


class TestValidateDeck:
    def test_valid_30_card_deck(self):
        cards = [_card(f"card_{i}") for i in range(15)]
        card_db = _card_db(cards)
        deck = DeckData(
            name="Valid", hero_class=HeroClass.MAGE,
            format=GameFormat.STANDARD,
            cards={f"card_{i}": 2 for i in range(15)}, source="manual",
        )
        errors = validate_deck(deck, card_db)
        assert errors == []

    def test_too_many_cards(self):
        cards = [_card(f"card_{i}") for i in range(16)]
        card_db = _card_db(cards)
        deck = DeckData(
            name="Too Many", hero_class=HeroClass.MAGE,
            format=GameFormat.STANDARD,
            cards={f"card_{i}": 2 for i in range(16)}, source="manual",
        )
        errors = validate_deck(deck, card_db)
        assert any("30" in str(e) for e in errors)

    def test_too_few_cards(self):
        cards = [_card("card_0")]
        card_db = _card_db(cards)
        deck = DeckData(
            name="Too Few", hero_class=HeroClass.MAGE,
            format=GameFormat.STANDARD, cards={"card_0": 1}, source="manual",
        )
        errors = validate_deck(deck, card_db)
        assert any("30" in str(e) for e in errors)

    def test_legendary_max_one_copy(self):
        cards = [_card("legend_1", rarity=Rarity.LEGENDARY)]
        cards += [_card(f"card_{i}") for i in range(14)]
        card_db = _card_db(cards)
        deck = DeckData(
            name="Bad Legendary", hero_class=HeroClass.MAGE,
            format=GameFormat.STANDARD,
            cards={"legend_1": 2, **{f"card_{i}": 2 for i in range(14)}},
            source="manual",
        )
        errors = validate_deck(deck, card_db)
        assert any("legendary" in str(e).lower() for e in errors)

    def test_wrong_class_card(self):
        warrior_card = _card("warrior_1", hero_class=HeroClass.WARRIOR)
        cards = [warrior_card] + [_card(f"card_{i}") for i in range(14)]
        card_db = _card_db(cards)
        deck = DeckData(
            name="Wrong Class", hero_class=HeroClass.MAGE,
            format=GameFormat.STANDARD,
            cards={"warrior_1": 2, **{f"card_{i}": 2 for i in range(14)}},
            source="manual",
        )
        errors = validate_deck(deck, card_db)
        assert any("class" in str(e).lower() for e in errors)

    def test_wild_card_in_standard_deck(self):
        wild_only = _card("wild_1", is_standard=False)
        cards = [wild_only] + [_card(f"card_{i}") for i in range(14)]
        card_db = _card_db(cards)
        deck = DeckData(
            name="Wild in Standard", hero_class=HeroClass.MAGE,
            format=GameFormat.STANDARD,
            cards={"wild_1": 2, **{f"card_{i}": 2 for i in range(14)}},
            source="manual",
        )
        errors = validate_deck(deck, card_db)
        assert any("standard" in str(e).lower() for e in errors)

    def test_wild_format_allows_all(self):
        wild_only = _card("wild_1", is_standard=False)
        cards = [wild_only] + [_card(f"card_{i}") for i in range(14)]
        card_db = _card_db(cards)
        deck = DeckData(
            name="Wild OK", hero_class=HeroClass.MAGE,
            format=GameFormat.WILD,
            cards={"wild_1": 2, **{f"card_{i}": 2 for i in range(14)}},
            source="manual",
        )
        errors = validate_deck(deck, card_db)
        assert errors == []

    def test_unknown_card_rejected(self):
        deck = DeckData(
            name="Unknown", hero_class=HeroClass.MAGE,
            format=GameFormat.STANDARD, cards={"nonexistent": 2}, source="manual",
        )
        errors = validate_deck(deck, {})
        assert any("not found" in str(e).lower() for e in errors)
