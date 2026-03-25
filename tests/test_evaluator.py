import pytest
from src.simulator.game_state import GameState, PlayerState, HeroState, MinionState
from src.simulator.evaluator import evaluate_state

def _state(**kw):
    return GameState(
        PlayerState(hero=HeroState("MAGE"), **kw),
        PlayerState(hero=HeroState("WARRIOR")),
    )

class TestEvaluator:
    def test_empty_board_equal(self):
        state = _state()
        score = evaluate_state(state, player_idx=0)
        assert score == pytest.approx(0, abs=5)

    def test_board_advantage(self):
        state = _state()
        state.player1.board = [MinionState("a","A",3,4,4,3)]
        score = evaluate_state(state, player_idx=0)
        assert score > 0

    def test_health_matters(self):
        state = _state()
        state.player1.hero.health = 10
        state.player2.hero.health = 30
        score = evaluate_state(state, player_idx=0)
        assert score < 0

    def test_lethal_is_max(self):
        state = _state()
        state.player2.hero.health = 0
        score = evaluate_state(state, player_idx=0)
        assert score > 900

    def test_dead_is_min(self):
        state = _state()
        state.player1.hero.health = 0
        score = evaluate_state(state, player_idx=0)
        assert score < -900

    def test_taunt_bonus(self):
        state = _state()
        m1 = MinionState("t","Taunt",2,5,5,3, taunt=True)
        state.player1.board = [m1]
        score_taunt = evaluate_state(state, player_idx=0)
        m1.taunt = False
        score_no_taunt = evaluate_state(state, player_idx=0)
        assert score_taunt > score_no_taunt

    def test_hand_advantage(self):
        s1 = _state(hand=["a","b","c","d"])
        s2 = _state(hand=["a"])
        assert evaluate_state(s1, 0) > evaluate_state(s2, 0)
