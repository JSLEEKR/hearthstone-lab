import pytest
from src.simulator.tournament import Tournament, TournamentResult

@pytest.fixture
def sample_card_db():
    return {f"c_{i}": {"card_id":f"c_{i}","card_type":"MINION",
        "mana_cost":(i%7)+1,"attack":(i%5)+1,"health":(i%5)+2,
        "mechanics":[],"name":f"C{i}"} for i in range(30)}

@pytest.fixture
def sample_decks():
    return {
        "Aggro": {"hero": "HUNTER", "cards": [f"c_{i}" for i in range(15)] * 2},
        "Control": {"hero": "WARRIOR", "cards": [f"c_{i}" for i in range(15)] * 2},
        "Midrange": {"hero": "MAGE", "cards": [f"c_{i}" for i in range(15)] * 2},
    }

class TestTournament:
    def test_round_robin_runs(self, sample_card_db, sample_decks):
        t = Tournament(sample_decks, sample_card_db, matches_per_pair=5)
        result = t.run()
        assert isinstance(result, TournamentResult)
        assert len(result.rankings) == 3

    def test_matchup_matrix(self, sample_card_db, sample_decks):
        t = Tournament(sample_decks, sample_card_db, matches_per_pair=5)
        result = t.run()
        assert len(result.matchups) > 0
        for mu in result.matchups:
            assert "deck_a" in mu
            assert "deck_b" in mu
            assert "a_wins" in mu
            assert "winrate_a" in mu

    def test_rankings_sorted(self, sample_card_db, sample_decks):
        t = Tournament(sample_decks, sample_card_db, matches_per_pair=5)
        result = t.run()
        winrates = [r["overall_winrate"] for r in result.rankings]
        assert winrates == sorted(winrates, reverse=True)

    def test_summary_text(self, sample_card_db, sample_decks):
        t = Tournament(sample_decks, sample_card_db, matches_per_pair=5)
        result = t.run()
        text = result.summary()
        assert "Aggro" in text
        assert "Control" in text
        assert "Rankings" in text
        assert "Matchup Matrix" in text

    def test_five_deck_tournament(self, sample_card_db):
        decks = {}
        classes = ["HUNTER", "WARRIOR", "MAGE", "PRIEST", "ROGUE"]
        for i, cls in enumerate(classes):
            cards = [f"c_{(j + i*3) % 30}" for j in range(15)] * 2
            decks[f"{cls.title()} Deck"] = {"hero": cls, "cards": cards}
        t = Tournament(decks, sample_card_db, matches_per_pair=5)
        result = t.run()
        assert len(result.rankings) == 5
        assert len(result.matchups) == 10  # C(5,2) = 10 pairs
