import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.db.tables import Base, Deck, HSReplayStats, Simulation, TierHistory
from src.tierlist.calculator import TierCalculator
from src.tierlist.ranker import TierRanker


@pytest.fixture
def tier_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for i in range(5):
            deck = Deck(name=f"Deck {i}", hero_class="MAGE", format="standard",
                        source="hsreplay")
            session.add(deck)
        session.commit()

        decks = session.query(Deck).all()
        winrates = [58.0, 54.0, 50.0, 47.0, 43.0]
        for deck, wr in zip(decks, winrates):
            session.add(HSReplayStats(
                deck_id=deck.id, winrate=wr, playrate=5.0, games_played=1000
            ))
        session.commit()
        yield session
    engine.dispose()


class TestTierCalculator:
    def test_calculate_combined_winrate_both_sources(self):
        calc = TierCalculator(weight_sim=0.5, weight_hsreplay=0.5)
        result = calc.combined_winrate(sim_winrate=60.0, hsreplay_winrate=50.0)
        assert result == 55.0

    def test_calculate_combined_winrate_sim_only(self):
        calc = TierCalculator(weight_sim=0.5, weight_hsreplay=0.5)
        result = calc.combined_winrate(sim_winrate=60.0, hsreplay_winrate=None)
        assert result == 60.0

    def test_calculate_combined_winrate_hsreplay_only(self):
        calc = TierCalculator(weight_sim=0.5, weight_hsreplay=0.5)
        result = calc.combined_winrate(sim_winrate=None, hsreplay_winrate=50.0)
        assert result == 50.0

    def test_calculate_combined_winrate_none(self):
        calc = TierCalculator(weight_sim=0.5, weight_hsreplay=0.5)
        result = calc.combined_winrate(sim_winrate=None, hsreplay_winrate=None)
        assert result is None

    def test_get_deck_winrates(self, tier_db):
        calc = TierCalculator(weight_sim=0.5, weight_hsreplay=0.5)
        results = calc.get_deck_winrates(tier_db, format_type="standard")
        assert len(results) == 5


class TestTierRanker:
    def test_assign_tier_s(self):
        ranker = TierRanker()
        assert ranker.assign_tier(58.0) == "S"

    def test_assign_tier_a(self):
        ranker = TierRanker()
        assert ranker.assign_tier(53.0) == "A"

    def test_assign_tier_b(self):
        ranker = TierRanker()
        assert ranker.assign_tier(50.0) == "B"

    def test_assign_tier_c(self):
        ranker = TierRanker()
        assert ranker.assign_tier(47.0) == "C"

    def test_assign_tier_d(self):
        ranker = TierRanker()
        assert ranker.assign_tier(43.0) == "D"

    def test_rank_decks(self, tier_db):
        calc = TierCalculator(weight_sim=0.5, weight_hsreplay=0.5)
        ranker = TierRanker()
        deck_winrates = calc.get_deck_winrates(tier_db, format_type="standard")
        ranked = ranker.rank_decks(deck_winrates)
        assert len(ranked) == 5
        assert ranked[0]["tier"] == "S"
        assert ranked[-1]["tier"] == "D"


class TestTierHistory:
    def test_record_tier(self, tier_db):
        from src.tierlist.history import TierHistoryTracker
        tracker = TierHistoryTracker(tier_db)
        tracker.record(
            deck_id=1, tier="S", sim_winrate=60.0,
            hsreplay_winrate=56.0, combined_winrate=58.0
        )
        records = tier_db.query(TierHistory).filter_by(deck_id=1).all()
        assert len(records) == 1
        assert records[0].tier == "S"

    def test_get_history(self, tier_db):
        from src.tierlist.history import TierHistoryTracker
        tracker = TierHistoryTracker(tier_db)
        tracker.record(deck_id=1, tier="S", sim_winrate=60.0,
                       hsreplay_winrate=56.0, combined_winrate=58.0)
        tracker.record(deck_id=1, tier="A", sim_winrate=55.0,
                       hsreplay_winrate=53.0, combined_winrate=54.0)
        history = tracker.get_history(deck_id=1)
        assert len(history) == 2

    def test_get_latest_tier(self, tier_db):
        from src.tierlist.history import TierHistoryTracker
        tracker = TierHistoryTracker(tier_db)
        tracker.record(deck_id=1, tier="S", sim_winrate=60.0,
                       hsreplay_winrate=56.0, combined_winrate=58.0)
        tracker.record(deck_id=1, tier="A", sim_winrate=55.0,
                       hsreplay_winrate=53.0, combined_winrate=54.0)
        latest = tracker.get_latest_tier(deck_id=1)
        assert latest == "A"
