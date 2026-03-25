import pytest
from src.simulator.game_state import GameState, PlayerState, HeroState, MinionState
from src.simulator.engine import GameEngine
from src.simulator.ai import RuleBasedAI, ScoreBasedAI, MCTSAI, BaseAI, SimpleAI
from src.simulator.actions import PlayCard, Attack, EndTurn, HeroPower


def _state(card_db=None, **kw):
    return GameState(
        PlayerState(hero=HeroState("MAGE"), **kw),
        PlayerState(hero=HeroState("WARRIOR")),
    ), GameEngine(card_db or {})


class TestSimpleAIBackwardCompat:
    """Ensure SimpleAI alias still works."""

    def test_simple_ai_is_rule_based(self):
        assert SimpleAI is RuleBasedAI

    def test_returns_end_turn_when_no_actions(self):
        ai = SimpleAI()
        state = GameState(
            player1=PlayerState(hero=HeroState(hero_class="MAGE"), mana=0),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        engine = GameEngine()
        action = ai.choose_action(state, engine)
        assert isinstance(action, EndTurn)

    def test_plays_affordable_minion(self):
        card_db = {"yeti": {"card_id": "yeti", "card_type": "MINION", "mana_cost": 4,
                            "attack": 4, "health": 5, "mechanics": []}}
        ai = SimpleAI()
        state = GameState(
            player1=PlayerState(hero=HeroState(hero_class="MAGE"), mana=4, max_mana=4, hand=["yeti"]),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        engine = GameEngine(card_db=card_db)
        action = ai.choose_action(state, engine)
        assert isinstance(action, PlayCard)

    def test_attacks_when_possible(self):
        ai = SimpleAI()
        state = GameState(
            player1=PlayerState(
                hero=HeroState(hero_class="MAGE"), mana=0,
                board=[MinionState(card_id="a", name="A", attack=3, health=2,
                                   max_health=2, mana_cost=2, summoned_this_turn=False)],
            ),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        engine = GameEngine()
        action = ai.choose_action(state, engine)
        assert isinstance(action, Attack)

    def test_mulligan_keeps_low_cost(self):
        ai = SimpleAI()
        card_db = {"cheap": {"mana_cost": 2}, "expensive": {"mana_cost": 7}, "mid": {"mana_cost": 4}}
        keep = ai.mulligan(["cheap", "expensive", "mid"], card_db)
        assert "cheap" in keep
        assert "expensive" not in keep


class TestRuleBasedAI:
    def test_plays_cards_before_attacking(self):
        card_db = {"c1": {"card_id": "c1", "card_type": "MINION", "mana_cost": 2,
            "attack": 3, "health": 2, "mechanics": [], "name": "C1"}}
        state, engine = _state(card_db, mana=5, max_mana=5, hand=["c1"])
        state.player1.board = [MinionState("a", "A", 2, 3, 3, 2, summoned_this_turn=False)]
        state.player2.board = [MinionState("b", "B", 1, 2, 2, 1)]
        ai = RuleBasedAI()
        action = ai.choose_action(state, engine)
        assert isinstance(action, PlayCard)

    def test_efficient_trade(self):
        """A 3/5 minion should prefer to kill the 3hp minion (kill+survive) over the 6hp one."""
        state, engine = _state()
        state.player1.board = [MinionState("a", "A", 3, 5, 5, 2, summoned_this_turn=False)]
        state.player2.board = [
            MinionState("b1", "B1", 2, 6, 6, 3),
            MinionState("b2", "B2", 2, 3, 3, 2),
        ]
        ai = RuleBasedAI()
        action = ai.choose_action(state, engine)
        assert isinstance(action, Attack)
        # b2 (idx 1) is a kill+survive trade, b1 is not a kill
        assert action.target_idx == 1

    def test_mulligan_keeps_low_cost(self):
        card_db = {"cheap": {"mana_cost": 2}, "expensive": {"mana_cost": 8}}
        ai = RuleBasedAI()
        keep = ai.mulligan(["cheap", "expensive"], card_db)
        assert "cheap" in keep
        assert "expensive" not in keep


class TestScoreBasedAI:
    def test_finds_lethal(self):
        state, engine = _state(mana=0, max_mana=10)
        state.player1.board = [MinionState("a", "A", 5, 3, 3, 3, summoned_this_turn=False)]
        state.player2.hero.health = 5
        ai = ScoreBasedAI()
        action = ai.choose_action(state, engine)
        assert isinstance(action, Attack)
        assert action.target_is_hero

    def test_prefers_value_trade(self):
        """A 5/6 should trade into a 2/5 (kill+survive) rather than go face for 5."""
        state, engine = _state(mana=0, max_mana=10)
        state.player1.board = [MinionState("a", "A", 5, 6, 6, 5, summoned_this_turn=False)]
        state.player2.board = [MinionState("b", "B", 2, 5, 5, 5)]
        state.player2.hero.health = 30
        ai = ScoreBasedAI()
        action = ai.choose_action(state, engine)
        assert isinstance(action, Attack)
        assert not action.target_is_hero


class TestMCTSAI:
    def test_finds_lethal(self):
        state, engine = _state(mana=0, max_mana=10)
        state.player1.board = [MinionState("a", "A", 7, 3, 3, 3, summoned_this_turn=False)]
        state.player2.hero.health = 5
        ai = MCTSAI(iterations=50)
        action = ai.choose_action(state, engine)
        assert isinstance(action, Attack)
        assert action.target_is_hero

    def test_completes_without_crash(self):
        card_db = {f"c_{i}": {"card_id": f"c_{i}", "card_type": "MINION",
            "mana_cost": (i % 7) + 1, "attack": (i % 5) + 1, "health": (i % 5) + 2,
            "mechanics": [], "name": f"C{i}"} for i in range(30)}
        state = GameState(
            PlayerState(hero=HeroState("MAGE"), mana=5, max_mana=5,
                        hand=["c_0", "c_1", "c_2"], deck=[f"c_{i}" for i in range(10)]),
            PlayerState(hero=HeroState("WARRIOR"),
                        board=[MinionState("e", "E", 3, 4, 4, 3)]),
        )
        engine = GameEngine(card_db)
        ai = MCTSAI(iterations=30)
        action = ai.choose_action(state, engine)
        assert action is not None


class TestMatchWithAI:
    def test_match_with_rule_based(self):
        from src.simulator.match import run_match
        card_db = {f"c_{i}": {"card_id": f"c_{i}", "card_type": "MINION",
            "mana_cost": (i % 7) + 1, "attack": (i % 5) + 1, "health": (i % 5) + 2,
            "mechanics": [], "name": f"C{i}"} for i in range(30)}
        deck = [f"c_{i}" for i in range(15)] * 2
        r = run_match(list(deck), list(deck), "MAGE", "WARRIOR", card_db,
                      ai_class=RuleBasedAI)
        assert r.winner in ("A", "B", None)

    def test_match_with_score_based(self):
        from src.simulator.match import run_match
        card_db = {f"c_{i}": {"card_id": f"c_{i}", "card_type": "MINION",
            "mana_cost": (i % 7) + 1, "attack": (i % 5) + 1, "health": (i % 5) + 2,
            "mechanics": [], "name": f"C{i}"} for i in range(30)}
        deck = [f"c_{i}" for i in range(15)] * 2
        r = run_match(list(deck), list(deck), "MAGE", "WARRIOR", card_db,
                      ai_class=ScoreBasedAI)
        assert r.winner in ("A", "B", None)

    def test_match_with_mcts(self):
        from src.simulator.match import run_match
        card_db = {f"c_{i}": {"card_id": f"c_{i}", "card_type": "MINION",
            "mana_cost": (i % 7) + 1, "attack": (i % 5) + 1, "health": (i % 5) + 2,
            "mechanics": [], "name": f"C{i}"} for i in range(30)}
        deck = [f"c_{i}" for i in range(15)] * 2
        r = run_match(list(deck), list(deck), "MAGE", "WARRIOR", card_db,
                      ai_class=MCTSAI(iterations=20))
        assert r.winner in ("A", "B", None)

    def test_backward_compatible(self):
        from src.simulator.match import run_match
        card_db = {f"c_{i}": {"card_id": f"c_{i}", "card_type": "MINION",
            "mana_cost": (i % 7) + 1, "attack": (i % 5) + 1, "health": (i % 5) + 2,
            "mechanics": [], "name": f"C{i}"} for i in range(30)}
        deck = [f"c_{i}" for i in range(15)] * 2
        r = run_match(list(deck), list(deck), "MAGE", "WARRIOR", card_db)
        assert r.winner in ("A", "B", None)
