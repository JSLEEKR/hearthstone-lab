import pytest
import sqlalchemy
from src.db.tables import Card, Deck, DeckCard, Simulation


class TestCardTable:
    def test_create_card(self, db_session):
        card = Card(
            card_id="CS2_182", dbf_id=1369, name="Chillwind Yeti",
            name_ko="칠풍의 예티", card_type="MINION", hero_class="NEUTRAL",
            mana_cost=4, attack=4, health=5, rarity="FREE", set_name="CORE",
            collectible=True, is_standard=True,
        )
        db_session.add(card)
        db_session.commit()
        result = db_session.query(Card).filter_by(card_id="CS2_182").one()
        assert result.name == "Chillwind Yeti"
        assert result.attack == 4

    def test_card_id_unique(self, db_session):
        card1 = Card(card_id="CS2_182", dbf_id=1369, name="A",
                     name_ko="A", card_type="MINION", hero_class="NEUTRAL",
                     mana_cost=1, rarity="FREE", set_name="CORE",
                     collectible=True, is_standard=True)
        card2 = Card(card_id="CS2_182", dbf_id=9999, name="B",
                     name_ko="B", card_type="MINION", hero_class="NEUTRAL",
                     mana_cost=1, rarity="FREE", set_name="CORE",
                     collectible=True, is_standard=True)
        db_session.add(card1)
        db_session.commit()
        db_session.add(card2)
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            db_session.commit()


class TestDeckTable:
    def test_create_deck(self, db_session):
        deck = Deck(hero_class="MAGE", name="Test Deck", archetype="aggro",
                    format="standard", deckstring="AAE...", source="manual")
        db_session.add(deck)
        db_session.commit()
        assert deck.id is not None
        assert deck.created_at is not None


class TestDeckCardTable:
    def test_deck_card_relationship(self, db_session):
        card = Card(card_id="CS2_182", dbf_id=1369, name="Yeti",
                    name_ko="예티", card_type="MINION", hero_class="NEUTRAL",
                    mana_cost=4, attack=4, health=5, rarity="FREE",
                    set_name="CORE", collectible=True, is_standard=True)
        deck = Deck(hero_class="MAGE", name="Test", format="standard", source="manual")
        db_session.add_all([card, deck])
        db_session.commit()
        dc = DeckCard(deck_id=deck.id, card_id=card.id, count=2)
        db_session.add(dc)
        db_session.commit()
        assert dc.count == 2


class TestSimulationTable:
    def test_create_simulation_with_winner(self, db_session):
        d1 = Deck(hero_class="MAGE", name="D1", format="standard", source="manual")
        d2 = Deck(hero_class="WARRIOR", name="D2", format="standard", source="manual")
        db_session.add_all([d1, d2])
        db_session.commit()
        sim = Simulation(deck_a_id=d1.id, deck_b_id=d2.id, winner_id=d1.id, turns=12)
        db_session.add(sim)
        db_session.commit()
        assert sim.winner_id == d1.id

    def test_create_simulation_draw(self, db_session):
        d1 = Deck(hero_class="MAGE", name="D1", format="standard", source="manual")
        d2 = Deck(hero_class="WARRIOR", name="D2", format="standard", source="manual")
        db_session.add_all([d1, d2])
        db_session.commit()
        sim = Simulation(deck_a_id=d1.id, deck_b_id=d2.id, winner_id=None, turns=45)
        db_session.add(sim)
        db_session.commit()
        assert sim.winner_id is None
