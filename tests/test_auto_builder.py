import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.db.tables import Base, Card
from src.deckbuilder.auto import AutoDeckBuilder


@pytest.fixture
def auto_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        cards = []
        for i in range(50):
            cards.append(Card(
                card_id=f"card_{i}", dbf_id=100+i, name=f"Card {i}",
                name_ko=f"카드 {i}", card_type="MINION", hero_class="NEUTRAL",
                mana_cost=i % 8 + 1, attack=i % 5 + 1, health=i % 5 + 1,
                rarity="COMMON" if i < 45 else "LEGENDARY",
                set_name="TEST", collectible=True, is_standard=True,
                mechanics=[]
            ))
        for i in range(10):
            cards.append(Card(
                card_id=f"mage_{i}", dbf_id=200+i, name=f"Mage Card {i}",
                name_ko=f"메이지 카드 {i}", card_type="SPELL" if i < 5 else "MINION",
                hero_class="MAGE", mana_cost=i % 6 + 1, attack=None if i < 5 else i,
                health=None if i < 5 else i + 1,
                rarity="COMMON", set_name="TEST", collectible=True,
                is_standard=True, mechanics=[]
            ))
        session.add_all(cards)
        session.commit()
        yield session
    engine.dispose()


class TestAutoDeckBuilder:
    def test_generate_deck_has_30_cards(self, auto_db):
        builder = AutoDeckBuilder(auto_db)
        deck = builder.generate_deck(hero_class="MAGE", format="standard")
        total = sum(c["count"] for c in deck["cards"])
        assert total == 30

    def test_generate_deck_correct_class(self, auto_db):
        builder = AutoDeckBuilder(auto_db)
        deck = builder.generate_deck(hero_class="MAGE", format="standard")
        assert deck["hero_class"] == "MAGE"

    def test_generate_deck_respects_legendary_limit(self, auto_db):
        builder = AutoDeckBuilder(auto_db)
        deck = builder.generate_deck(hero_class="MAGE", format="standard")
        for c in deck["cards"]:
            if c["rarity"] == "LEGENDARY":
                assert c["count"] == 1

    def test_generate_deck_has_mana_curve(self, auto_db):
        builder = AutoDeckBuilder(auto_db)
        deck = builder.generate_deck(hero_class="MAGE", format="standard")
        costs = {}
        for c in deck["cards"]:
            cost = c["mana_cost"]
            costs[cost] = costs.get(cost, 0) + c["count"]
        assert len(costs) >= 3

    def test_generate_aggro_deck_low_curve(self, auto_db):
        builder = AutoDeckBuilder(auto_db)
        deck = builder.generate_deck(hero_class="MAGE", format="standard",
                                      archetype="aggro")
        total_cost = sum(c["mana_cost"] * c["count"] for c in deck["cards"])
        total_cards = sum(c["count"] for c in deck["cards"])
        avg = total_cost / total_cards
        assert avg <= 4.0
