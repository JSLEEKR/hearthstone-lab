import pytest
from src.core.enums import CardType, Rarity, HeroClass, GameFormat, Archetype
from src.core.models import CardData, DeckData


class TestCardData:
    def test_create_minion(self):
        card = CardData(
            card_id="CS2_182", dbf_id=1369, name="Chillwind Yeti",
            name_ko="칠풍의 예티", card_type=CardType.MINION,
            hero_class=HeroClass.NEUTRAL, mana_cost=4, attack=4, health=5,
            rarity=Rarity.FREE, set_name="CORE", collectible=True, is_standard=True,
        )
        assert card.card_id == "CS2_182"
        assert card.attack == 4
        assert card.health == 5

    def test_create_spell(self):
        card = CardData(
            card_id="CS2_029", dbf_id=522, name="Fireball", name_ko="화염구",
            card_type=CardType.SPELL, hero_class=HeroClass.MAGE, mana_cost=4,
            rarity=Rarity.FREE, set_name="CORE", collectible=True, is_standard=True,
        )
        assert card.attack is None
        assert card.health is None

    def test_create_weapon(self):
        card = CardData(
            card_id="CS2_106", dbf_id=401, name="Fiery War Axe",
            name_ko="불타는 전쟁도끼", card_type=CardType.WEAPON,
            hero_class=HeroClass.WARRIOR, mana_cost=3, attack=3, durability=2,
            rarity=Rarity.FREE, set_name="CORE", collectible=True, is_standard=True,
        )
        assert card.durability == 2

    def test_mechanics_default_empty(self):
        card = CardData(
            card_id="CS2_182", dbf_id=1369, name="Chillwind Yeti",
            name_ko="칠풍의 예티", card_type=CardType.MINION,
            hero_class=HeroClass.NEUTRAL, mana_cost=4, attack=4, health=5,
            rarity=Rarity.FREE, set_name="CORE", collectible=True, is_standard=True,
        )
        assert card.mechanics == []

    def test_negative_mana_cost_rejected(self):
        with pytest.raises(ValueError):
            CardData(
                card_id="BAD", dbf_id=1, name="Bad", name_ko="나쁨",
                card_type=CardType.MINION, hero_class=HeroClass.NEUTRAL,
                mana_cost=-1, rarity=Rarity.FREE, set_name="CORE",
                collectible=True, is_standard=True,
            )


class TestDeckData:
    def test_create_deck(self):
        deck = DeckData(
            name="Test Deck", hero_class=HeroClass.MAGE,
            format=GameFormat.STANDARD, cards={"CS2_029": 2, "CS2_182": 2},
            source="manual",
        )
        assert deck.name == "Test Deck"
        assert deck.hero_class == HeroClass.MAGE
        assert deck.total_cards == 4

    def test_archetype_default_none(self):
        deck = DeckData(
            name="Test", hero_class=HeroClass.MAGE,
            format=GameFormat.STANDARD, cards={}, source="manual",
        )
        assert deck.archetype is None

    def test_deckstring_optional(self):
        deck = DeckData(
            name="Test", hero_class=HeroClass.MAGE,
            format=GameFormat.STANDARD, cards={}, source="manual",
        )
        assert deck.deckstring is None
