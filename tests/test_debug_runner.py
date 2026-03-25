import pytest
from src.simulator.debug_runner import DebugRunner


@pytest.fixture
def simple_game():
    card_db = {
        f"card_{i}": {
            "card_id": f"card_{i}", "card_type": "MINION",
            "mana_cost": (i % 4) + 1, "attack": (i % 3) + 1,
            "health": (i % 3) + 2, "mechanics": [], "name": f"Minion {i}",
        }
        for i in range(30)
    }
    deck = [f"card_{i}" for i in range(15)] * 2
    return DebugRunner(
        deck_a=deck, deck_b=deck,
        hero_a="MAGE", hero_b="WARRIOR",
        card_db=card_db, seed=42,
    )


class TestDebugRunner:
    def test_setup(self, simple_game):
        result = simple_game.setup()
        assert result["game_over"] is False

    def test_start_turn(self, simple_game):
        simple_game.setup()
        result = simple_game.start_turn()
        assert result["turn"] == 1

    def test_auto_turn(self, simple_game):
        simple_game.setup()
        result = simple_game.auto_turn()
        assert result["turn"] == 1

    def test_run_game(self, simple_game):
        result = simple_game.run_game()
        assert result["turns"] > 0
        assert "log" in result

    def test_format_board(self, simple_game):
        simple_game.setup()
        simple_game.start_turn()
        board = simple_game.format_board()
        assert "Player 1" in board
        assert "Player 2" in board
        assert "MAGE" in board
        assert "WARRIOR" in board

    def test_get_actions(self, simple_game):
        simple_game.setup()
        simple_game.start_turn()
        actions = simple_game.get_actions()
        assert len(actions) > 0  # at least EndTurn

    def test_execute_action(self, simple_game):
        simple_game.setup()
        simple_game.start_turn()
        actions = simple_game.get_actions()
        result = simple_game.execute(actions[0])
        assert "game_over" in result

    def test_seed_reproducibility(self):
        card_db = {f"c_{i}": {"card_id": f"c_{i}", "card_type": "MINION", "mana_cost": 2, "attack": 2, "health": 2, "mechanics": [], "name": f"M{i}"} for i in range(30)}
        deck = [f"c_{i}" for i in range(15)] * 2
        r1 = DebugRunner(deck, deck, "MAGE", "MAGE", card_db, seed=123)
        r2 = DebugRunner(deck, deck, "MAGE", "MAGE", card_db, seed=123)
        res1 = r1.run_game()
        res2 = r2.run_game()
        assert res1["winner"] == res2["winner"]
        assert res1["turns"] == res2["turns"]
