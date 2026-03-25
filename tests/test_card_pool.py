import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.db.tables import Base, Card
from src.simulator.card_pool import CardPoolManager, CardPoolFilter, POOL_PRESETS
import json


@pytest.fixture
def pool_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        # Seed test cards with varied properties
        test_cards = [
            Card(card_id="beast_1", dbf_id=1, name="Test Beast", name_ko="테스트 야수",
                 card_type="MINION", hero_class="HUNTER", mana_cost=3, attack=3, health=2,
                 rarity="COMMON", set_name="TEST", collectible=True, is_standard=True,
                 mechanics=["BATTLECRY"], json_data={"race": "BEAST"}),
            Card(card_id="dragon_1", dbf_id=2, name="Test Dragon", name_ko="테스트 용",
                 card_type="MINION", hero_class="NEUTRAL", mana_cost=5, attack=4, health=5,
                 rarity="RARE", set_name="TEST", collectible=True, is_standard=True,
                 mechanics=["TAUNT"], json_data={"race": "DRAGON"}),
            Card(card_id="spell_1", dbf_id=3, name="Fire Spell", name_ko="화염 주문",
                 card_type="SPELL", hero_class="MAGE", mana_cost=4, rarity="COMMON",
                 set_name="TEST", collectible=True, is_standard=True,
                 mechanics=[], json_data={"spellSchool": "FIRE"}),
            Card(card_id="spell_2", dbf_id=4, name="Frost Spell", name_ko="냉기 주문",
                 card_type="SPELL", hero_class="MAGE", mana_cost=3, rarity="RARE",
                 set_name="TEST", collectible=True, is_standard=True,
                 mechanics=[], json_data={"spellSchool": "FROST"}),
            Card(card_id="neutral_1", dbf_id=5, name="Neutral Minion", name_ko="중립 하수인",
                 card_type="MINION", hero_class="NEUTRAL", mana_cost=2, attack=2, health=3,
                 rarity="COMMON", set_name="TEST", collectible=True, is_standard=True,
                 mechanics=[], json_data={}),
            Card(card_id="demon_1", dbf_id=6, name="Test Demon", name_ko="테스트 악마",
                 card_type="MINION", hero_class="WARLOCK", mana_cost=1, attack=1, health=3,
                 rarity="COMMON", set_name="TEST", collectible=True, is_standard=False,
                 mechanics=["DEATHRATTLE"], json_data={"race": "DEMON"}),
            Card(card_id="legend_1", dbf_id=7, name="Legendary", name_ko="전설 카드",
                 card_type="MINION", hero_class="NEUTRAL", mana_cost=7, attack=7, health=7,
                 rarity="LEGENDARY", set_name="TEST", collectible=True, is_standard=True,
                 mechanics=["BATTLECRY"], json_data={}),
            Card(card_id="weapon_1", dbf_id=8, name="Test Weapon", name_ko="테스트 무기",
                 card_type="WEAPON", hero_class="WARRIOR", mana_cost=3, attack=3, health=None,
                 rarity="COMMON", set_name="TEST", collectible=True, is_standard=True,
                 mechanics=[], json_data={"durability": 2}),
            Card(card_id="secret_1", dbf_id=9, name="Test Secret", name_ko="테스트 비밀",
                 card_type="SPELL", hero_class="MAGE", mana_cost=3, rarity="RARE",
                 set_name="TEST", collectible=True, is_standard=True,
                 mechanics=["SECRET"], json_data={}),
            Card(card_id="all_tribe", dbf_id=10, name="Amalgam", name_ko="혼합체",
                 card_type="MINION", hero_class="NEUTRAL", mana_cost=3, attack=3, health=3,
                 rarity="EPIC", set_name="TEST", collectible=True, is_standard=True,
                 mechanics=[], json_data={"race": "ALL"}),
        ]
        session.add_all(test_cards)
        session.commit()
        yield session
    engine.dispose()


class TestCardPoolFilter:
    def test_filter_minions(self, pool_db):
        mgr = CardPoolManager(pool_db)
        results = mgr.query(CardPoolFilter(card_type="MINION"))
        assert all(c["card_type"] == "MINION" for c in results)
        assert len(results) >= 5

    def test_filter_spells(self, pool_db):
        mgr = CardPoolManager(pool_db)
        results = mgr.query(CardPoolFilter(card_type="SPELL"))
        assert all(c["card_type"] == "SPELL" for c in results)

    def test_filter_by_tribe_beast(self, pool_db):
        mgr = CardPoolManager(pool_db)
        results = mgr.query(CardPoolFilter(card_type="MINION", tribe="BEAST"))
        assert len(results) >= 1
        # ALL tribe should also match
        all_tribe = [c for c in results if c["card_id"] == "all_tribe"]
        assert len(all_tribe) == 1

    def test_filter_by_tribe_dragon(self, pool_db):
        mgr = CardPoolManager(pool_db)
        results = mgr.query(CardPoolFilter(card_type="MINION", tribe="DRAGON"))
        assert any(c["card_id"] == "dragon_1" for c in results)
        assert any(c["card_id"] == "all_tribe" for c in results)

    def test_filter_standard_only(self, pool_db):
        mgr = CardPoolManager(pool_db)
        results = mgr.query(CardPoolFilter(is_standard=True))
        assert all(c["card_id"] != "demon_1" for c in results)

    def test_filter_class_includes_neutral(self, pool_db):
        mgr = CardPoolManager(pool_db)
        results = mgr.query(CardPoolFilter(hero_class="HUNTER"))
        assert any(c["hero_class"] == "HUNTER" for c in results)
        assert any(c["hero_class"] == "NEUTRAL" for c in results)

    def test_filter_class_excludes_neutral(self, pool_db):
        mgr = CardPoolManager(pool_db)
        results = mgr.query(CardPoolFilter(hero_class="HUNTER", include_neutral=False))
        assert all(c["hero_class"] == "HUNTER" for c in results)

    def test_filter_by_mechanic(self, pool_db):
        mgr = CardPoolManager(pool_db)
        results = mgr.query(CardPoolFilter(mechanic="DEATHRATTLE"))
        assert len(results) >= 1

    def test_filter_odd_cost(self, pool_db):
        mgr = CardPoolManager(pool_db)
        results = mgr.query(CardPoolFilter(odd_cost=True))
        assert all(c["mana_cost"] % 2 == 1 for c in results)

    def test_filter_spell_school(self, pool_db):
        mgr = CardPoolManager(pool_db)
        results = mgr.query(CardPoolFilter(card_type="SPELL", spell_school="FIRE"))
        assert len(results) >= 1
        assert all(c["spell_school"] == "FIRE" for c in results)

    def test_filter_rarity(self, pool_db):
        mgr = CardPoolManager(pool_db)
        results = mgr.query(CardPoolFilter(rarity="LEGENDARY"))
        assert all(c["rarity"] == "LEGENDARY" for c in results)

    def test_exact_cost(self, pool_db):
        mgr = CardPoolManager(pool_db)
        results = mgr.query(CardPoolFilter(exact_cost=3))
        assert all(c["mana_cost"] == 3 for c in results)


class TestCardPoolManager:
    def test_random_cards(self, pool_db):
        mgr = CardPoolManager(pool_db)
        results = mgr.random_cards(CardPoolFilter(card_type="MINION"), count=3)
        assert len(results) == 3

    def test_discover(self, pool_db):
        mgr = CardPoolManager(pool_db)
        results = mgr.discover(CardPoolFilter(card_type="SPELL"), count=3)
        assert len(results) <= 3
        ids = [c["card_id"] for c in results]
        assert len(ids) == len(set(ids))  # no duplicates

    def test_discover_with_class_bonus(self, pool_db):
        mgr = CardPoolManager(pool_db)
        # Run discover many times and check class cards appear more often
        class_count = 0
        total = 0
        for _ in range(100):
            results = mgr.discover(CardPoolFilter(card_type="SPELL"), count=1, class_bonus="MAGE")
            if results and results[0]["hero_class"] == "MAGE":
                class_count += 1
            total += 1
        # With 4x bonus, MAGE should appear much more than 50%
        assert class_count > 60

    def test_cache_works(self, pool_db):
        mgr = CardPoolManager(pool_db)
        f = CardPoolFilter(card_type="MINION")
        r1 = mgr.query(f)
        r2 = mgr.query(f)
        assert r1 is r2  # same object from cache


class TestPoolPresets:
    def test_presets_are_valid(self, pool_db):
        mgr = CardPoolManager(pool_db)
        for name, f in POOL_PRESETS.items():
            results = mgr.query(f)
            assert isinstance(results, list), f"Preset {name} failed"
