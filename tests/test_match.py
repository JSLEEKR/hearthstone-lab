import pytest
from src.simulator.match import run_match, MatchResult

CARD_DB = {
    f"card_{i}": {
        "card_id": f"card_{i}", "card_type": "MINION",
        "mana_cost": (i % 8) + 1, "attack": (i % 5) + 1,
        "health": (i % 5) + 1, "mechanics": [], "name": f"Card {i}",
    }
    for i in range(30)
}


class TestRunMatch:
    def test_match_completes(self):
        deck_a = [f"card_{i}" for i in range(15)] * 2
        deck_b = [f"card_{i}" for i in range(15)] * 2
        result = run_match(deck_a=deck_a, deck_b=deck_b, hero_a="MAGE",
                           hero_b="WARRIOR", card_db=CARD_DB, max_turns=45)
        assert isinstance(result, MatchResult)
        assert result.turns > 0
        assert result.turns <= 45

    def test_match_has_winner_or_draw(self):
        deck_a = [f"card_{i}" for i in range(15)] * 2
        deck_b = [f"card_{i}" for i in range(15)] * 2
        result = run_match(deck_a=deck_a, deck_b=deck_b, hero_a="MAGE",
                           hero_b="WARRIOR", card_db=CARD_DB, max_turns=45)
        assert result.winner in ("A", "B", None)

    def test_match_respects_max_turns(self):
        deck_a = ["card_0"] * 2
        deck_b = ["card_0"] * 2
        result = run_match(deck_a=deck_a, deck_b=deck_b, hero_a="MAGE",
                           hero_b="WARRIOR", card_db=CARD_DB, max_turns=10)
        assert result.turns <= 10
