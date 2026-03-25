import pytest
from src.simulator.game_state import GameState, PlayerState, HeroState, MinionState
from src.simulator.engine import GameEngine


def _make_game(p1_deck=None, p2_deck=None):
    return GameState(
        player1=PlayerState(hero=HeroState(hero_class="MAGE"),
                            deck=list(p1_deck or [f"card_{i}" for i in range(30)])),
        player2=PlayerState(hero=HeroState(hero_class="WARRIOR"),
                            deck=list(p2_deck or [f"card_{i}" for i in range(30)])),
    )


class TestGameEngine:
    def test_start_game_draws_cards(self):
        engine = GameEngine()
        state = _make_game()
        engine.start_game(state)
        assert len(state.player1.hand) == 3
        assert len(state.player2.hand) == 5  # 4 cards + The Coin
        assert "GAME_005" in state.player2.hand

    def test_start_turn_gives_mana(self):
        engine = GameEngine()
        state = _make_game()
        engine.start_game(state)
        engine.start_turn(state)
        assert state.current_player.max_mana == 1
        assert state.current_player.mana == 1

    def test_mana_caps_at_10(self):
        engine = GameEngine()
        state = _make_game()
        state.current_player.max_mana = 10
        engine.start_turn(state)
        assert state.current_player.max_mana == 10
        assert state.current_player.mana == 10

    def test_start_turn_draws_card(self):
        engine = GameEngine()
        state = _make_game()
        engine.start_game(state)
        initial_hand = len(state.current_player.hand)
        engine.start_turn(state)
        assert len(state.current_player.hand) == initial_hand + 1

    def test_minion_combat(self):
        engine = GameEngine()
        m1 = MinionState(card_id="a", name="A", attack=3, health=5, max_health=5, mana_cost=3, summoned_this_turn=False)
        m2 = MinionState(card_id="b", name="B", attack=2, health=4, max_health=4, mana_cost=2)
        engine.resolve_combat(m1, m2)
        assert m1.health == 3
        assert m2.health == 1

    def test_hero_attack(self):
        engine = GameEngine()
        state = _make_game()
        m1 = MinionState(card_id="a", name="A", attack=5, health=2, max_health=2, mana_cost=2, summoned_this_turn=False)
        engine.attack_hero(m1, state.player2.hero)
        assert state.player2.hero.health == 25

    def test_dead_minions_removed(self):
        engine = GameEngine()
        state = _make_game()
        m1 = MinionState(card_id="a", name="A", attack=4, health=1, max_health=1, mana_cost=1, summoned_this_turn=False)
        m2 = MinionState(card_id="b", name="B", attack=4, health=1, max_health=1, mana_cost=1)
        state.player1.board.append(m1)
        state.player2.board.append(m2)
        engine.resolve_combat(m1, m2)
        engine.remove_dead_minions(state)
        assert len(state.player1.board) == 0
        assert len(state.player2.board) == 0

    def test_end_turn_resets_attacks(self):
        engine = GameEngine()
        state = _make_game()
        m = MinionState(card_id="a", name="A", attack=2, health=3, max_health=3, mana_cost=2,
                        summoned_this_turn=False, attacks_this_turn=1)
        state.current_player.board.append(m)
        engine.end_turn(state)
        prev_player = state.opponent
        assert prev_player.board[0].attacks_this_turn == 0
        assert prev_player.board[0].summoned_this_turn is False
