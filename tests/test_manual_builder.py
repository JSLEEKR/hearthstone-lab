import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.db.tables import Base, Card, Deck, DeckCard
from src.deckbuilder.manual import ManualDeckBuilder


@pytest.fixture
def builder_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        cards = [
            Card(card_id=f"card_{i}", dbf_id=100+i, name=f"Card {i}",
                 name_ko=f"\uce74\ub4dc {i}", card_type="MINION", hero_class="NEUTRAL",
                 mana_cost=i % 8 + 1, attack=i % 5 + 1, health=i % 5 + 1,
                 rarity="COMMON" if i < 28 else "LEGENDARY",
                 set_name="TEST", collectible=True, is_standard=True,
                 mechanics=[])
            for i in range(30)
        ]
        mage_card = Card(card_id="mage_1", dbf_id=200, name="Mage Spell",
                         name_ko="\uba54\uc774\uc9c0 \uc8fc\ubb38", card_type="SPELL", hero_class="MAGE",
                         mana_cost=3, rarity="RARE", set_name="TEST",
                         collectible=True, is_standard=True, mechanics=[])
        cards.append(mage_card)
        session.add_all(cards)
        session.commit()
        yield session
    engine.dispose()


class TestManualDeckBuilder:
    def test_search_cards_by_name(self, builder_db):
        builder = ManualDeckBuilder(builder_db)
        results = builder.search_cards(query="Card 1")
        assert len(results) >= 1
        assert any(c.name == "Card 1" for c in results)

    def test_search_cards_by_class(self, builder_db):
        builder = ManualDeckBuilder(builder_db)
        results = builder.search_cards(hero_class="MAGE")
        assert any(c.hero_class == "MAGE" for c in results)
        assert any(c.hero_class == "NEUTRAL" for c in results)

    def test_search_cards_by_mana_cost(self, builder_db):
        builder = ManualDeckBuilder(builder_db)
        results = builder.search_cards(mana_cost=3)
        assert all(c.mana_cost == 3 for c in results)

    def test_create_deck(self, builder_db):
        builder = ManualDeckBuilder(builder_db)
        deck = builder.create_deck(name="Test Deck", hero_class="MAGE", format="standard")
        assert deck.id is not None
        assert deck.hero_class == "MAGE"

    def test_add_card_to_deck(self, builder_db):
        builder = ManualDeckBuilder(builder_db)
        deck = builder.create_deck(name="Test", hero_class="MAGE", format="standard")
        result = builder.add_card(deck.id, "card_0")
        assert result is True

    def test_add_card_twice(self, builder_db):
        builder = ManualDeckBuilder(builder_db)
        deck = builder.create_deck(name="Test", hero_class="MAGE", format="standard")
        builder.add_card(deck.id, "card_0")
        result = builder.add_card(deck.id, "card_0")
        assert result is True

    def test_add_legendary_twice_fails(self, builder_db):
        builder = ManualDeckBuilder(builder_db)
        deck = builder.create_deck(name="Test", hero_class="MAGE", format="standard")
        builder.add_card(deck.id, "card_28")  # legendary
        result = builder.add_card(deck.id, "card_28")
        assert result is False

    def test_remove_card(self, builder_db):
        builder = ManualDeckBuilder(builder_db)
        deck = builder.create_deck(name="Test", hero_class="MAGE", format="standard")
        builder.add_card(deck.id, "card_0")
        result = builder.remove_card(deck.id, "card_0")
        assert result is True

    def test_get_deck_cards(self, builder_db):
        builder = ManualDeckBuilder(builder_db)
        deck = builder.create_deck(name="Test", hero_class="MAGE", format="standard")
        builder.add_card(deck.id, "card_0")
        builder.add_card(deck.id, "card_0")
        builder.add_card(deck.id, "card_1")
        cards = builder.get_deck_cards(deck.id)
        assert len(cards) == 2
        assert any(c["count"] == 2 for c in cards)
