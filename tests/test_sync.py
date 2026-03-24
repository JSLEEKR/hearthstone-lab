import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.db.tables import Base, Card
from src.collector.sync import sync_cards_to_db


@pytest.fixture
def sync_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


SAMPLE_HS_JSON_CARDS = [
    {
        "card_id": "CS2_182", "dbf_id": 1369, "name": "Chillwind Yeti",
        "name_ko": "칠풍의 예티", "card_type": "MINION", "hero_class": "NEUTRAL",
        "mana_cost": 4, "attack": 4, "health": 5, "durability": None,
        "text": "", "rarity": "FREE", "set_name": "CORE",
        "mechanics": [], "collectible": True, "json_data": {"id": "CS2_182"},
    },
    {
        "card_id": "CS2_029", "dbf_id": 522, "name": "Fireball",
        "name_ko": "화염구", "card_type": "SPELL", "hero_class": "MAGE",
        "mana_cost": 4, "attack": None, "health": None, "durability": None,
        "text": "Deal 6 damage.", "rarity": "FREE", "set_name": "CORE",
        "mechanics": [], "collectible": True, "json_data": {"id": "CS2_029"},
    },
]

SAMPLE_BLIZZARD_CARDS = [
    {"dbf_id": 1369, "name": "Chillwind Yeti",
     "flavor_text": "He always wanted to be a Chillwind Abominable.", "raw_data": {}},
]


def test_sync_inserts_new_cards(sync_db):
    stats = sync_cards_to_db(sync_db, SAMPLE_HS_JSON_CARDS, [])
    assert stats["inserted"] == 2
    assert stats["updated"] == 0
    assert sync_db.query(Card).count() == 2


def test_sync_updates_existing_cards(sync_db):
    sync_cards_to_db(sync_db, SAMPLE_HS_JSON_CARDS, [])
    updated_cards = [{**SAMPLE_HS_JSON_CARDS[0], "mana_cost": 5}, SAMPLE_HS_JSON_CARDS[1]]
    stats = sync_cards_to_db(sync_db, updated_cards, [])
    assert stats["updated"] == 1
    assert stats["inserted"] == 0
    card = sync_db.query(Card).filter_by(card_id="CS2_182").one()
    assert card.mana_cost == 5


def test_sync_merges_blizzard_flavor_text(sync_db):
    sync_cards_to_db(sync_db, SAMPLE_HS_JSON_CARDS, SAMPLE_BLIZZARD_CARDS)
    card = sync_db.query(Card).filter_by(card_id="CS2_182").one()
    assert card.json_data.get("flavor_text") == "He always wanted to be a Chillwind Abominable."


def test_sync_hearthstone_json_takes_priority(sync_db):
    blizzard_diff = [{"dbf_id": 1369, "name": "Different Name", "flavor_text": "Flavor", "raw_data": {}}]
    sync_cards_to_db(sync_db, SAMPLE_HS_JSON_CARDS, blizzard_diff)
    card = sync_db.query(Card).filter_by(card_id="CS2_182").one()
    assert card.name == "Chillwind Yeti"
