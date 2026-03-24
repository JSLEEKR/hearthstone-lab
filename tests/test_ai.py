import pytest
from src.simulator.game_state import GameState, PlayerState, HeroState, MinionState
from src.simulator.ai import SimpleAI
from src.simulator.engine import GameEngine
from src.simulator.actions import EndTurn, PlayCard, Attack


class TestSimpleAI:
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
