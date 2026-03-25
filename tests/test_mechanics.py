import pytest
from src.simulator.game_state import GameState, PlayerState, HeroState, MinionState
from src.simulator.engine import GameEngine


def _make_game():
    return GameState(
        player1=PlayerState(hero=HeroState(hero_class="MAGE"),
                            deck=[f"card_{i}" for i in range(30)]),
        player2=PlayerState(hero=HeroState(hero_class="WARRIOR"),
                            deck=[f"card_{i}" for i in range(30)]),
    )


class TestPoisonous:
    def test_poisonous_kills(self):
        engine = GameEngine()
        state = _make_game()
        attacker = MinionState(
            card_id="a", name="Cobra", attack=1, health=2, max_health=2,
            mana_cost=1, poisonous=True, summoned_this_turn=False,
        )
        defender = MinionState(
            card_id="b", name="Giant", attack=1, health=100, max_health=100,
            mana_cost=10,
        )
        state.player1.board.append(attacker)
        state.player2.board.append(defender)
        engine.resolve_combat(attacker, defender, state=state)
        assert defender.health == 0
        assert defender.is_dead

    def test_poisonous_blocked_by_divine_shield(self):
        engine = GameEngine()
        state = _make_game()
        attacker = MinionState(
            card_id="a", name="Cobra", attack=1, health=2, max_health=2,
            mana_cost=1, poisonous=True, summoned_this_turn=False,
        )
        defender = MinionState(
            card_id="b", name="Shielded", attack=1, health=5, max_health=5,
            mana_cost=3, divine_shield=True,
        )
        state.player1.board.append(attacker)
        state.player2.board.append(defender)
        engine.resolve_combat(attacker, defender, state=state)
        # Divine shield absorbs, so poisonous should NOT kill
        assert defender.health == 5
        assert not defender.is_dead
        assert not defender.divine_shield  # shield was popped


class TestLifesteal:
    def test_lifesteal_heals_hero(self):
        engine = GameEngine()
        state = _make_game()
        state.player1.hero.health = 20
        attacker = MinionState(
            card_id="a", name="Lifesteal Guy", attack=3, health=5, max_health=5,
            mana_cost=3, lifesteal=True, summoned_this_turn=False,
        )
        defender = MinionState(
            card_id="b", name="Target", attack=1, health=10, max_health=10,
            mana_cost=5,
        )
        state.player1.board.append(attacker)
        state.player2.board.append(defender)
        engine.resolve_combat(attacker, defender, state=state)
        assert state.player1.hero.health == 23  # healed for 3

    def test_lifesteal_no_overheal(self):
        engine = GameEngine()
        state = _make_game()
        state.player1.hero.health = 29  # only 1 below max
        attacker = MinionState(
            card_id="a", name="Lifesteal Guy", attack=5, health=5, max_health=5,
            mana_cost=3, lifesteal=True, summoned_this_turn=False,
        )
        defender = MinionState(
            card_id="b", name="Target", attack=1, health=10, max_health=10,
            mana_cost=5,
        )
        state.player1.board.append(attacker)
        state.player2.board.append(defender)
        engine.resolve_combat(attacker, defender, state=state)
        assert state.player1.hero.health == 30  # capped at max


class TestReborn:
    def test_reborn_respawns(self):
        engine = GameEngine()
        state = _make_game()
        minion = MinionState(
            card_id="a", name="Reborn Guy", attack=2, health=1, max_health=1,
            mana_cost=2, reborn=True,
        )
        state.player1.board.append(minion)
        minion.health = 0  # kill it
        engine.remove_dead_minions(state)
        assert len(state.player1.board) == 1
        reborn_minion = state.player1.board[0]
        assert reborn_minion.health == 1
        assert reborn_minion.max_health == 1
        assert reborn_minion.reborn is False

    def test_reborn_only_once(self):
        engine = GameEngine()
        state = _make_game()
        minion = MinionState(
            card_id="a", name="Reborn Guy", attack=2, health=1, max_health=1,
            mana_cost=2, reborn=True,
        )
        state.player1.board.append(minion)
        minion.health = 0
        engine.remove_dead_minions(state)
        # Now the reborn copy should have reborn=False
        reborn_minion = state.player1.board[0]
        assert reborn_minion.reborn is False
        # Kill the reborn copy
        reborn_minion.health = 0
        engine.remove_dead_minions(state)
        # Should not respawn again
        assert len(state.player1.board) == 0


class TestFreeze:
    def test_freeze_applied_on_combat(self):
        engine = GameEngine()
        state = _make_game()
        attacker = MinionState(
            card_id="a", name="Freezer", attack=2, health=5, max_health=5,
            mana_cost=2, mechanics=["FREEZE"], summoned_this_turn=False,
        )
        defender = MinionState(
            card_id="b", name="Target", attack=1, health=5, max_health=5,
            mana_cost=2,
        )
        state.player1.board.append(attacker)
        state.player2.board.append(defender)
        engine.resolve_combat(attacker, defender, state=state)
        assert defender.frozen is True
        assert attacker.frozen is False  # defender has no FREEZE


class TestOverload:
    def test_overload_reduces_next_turn(self):
        engine = GameEngine()
        state = _make_game()
        engine.start_game(state)
        engine.start_turn(state)  # turn 1, 1 mana
        # Play a card with overload
        card_data = {
            "card_id": "overload_card", "name": "Overloader",
            "card_type": "MINION", "mana_cost": 1, "attack": 3, "health": 2,
            "mechanics": [], "overload": 2,
        }
        engine.play_minion(state, card_data)
        assert state.current_player.overload == 2
        # End turn, switch, end that turn, switch back
        engine.end_turn(state)
        engine.start_turn(state)  # opponent turn
        engine.end_turn(state)
        engine.start_turn(state)  # our turn again, turn 2 => 2 mana - 2 overload = 0
        assert state.current_player.mana == 0
        assert state.current_player.overload == 0  # cleared after applying


class TestHeroAttackLimit:
    def test_hero_attack_limited_once(self):
        engine = GameEngine()
        state = _make_game()
        state.current_player.hero.attack = 3
        # Initially, hero can attack
        actions = engine.get_legal_actions(state)
        hero_attacks = [a for a in actions
                        if hasattr(a, 'attacker_idx') and a.attacker_idx == -1]
        assert len(hero_attacks) > 0

        # After attacking, hero.attacks_this_turn = 1
        state.current_player.hero.attacks_this_turn = 1
        actions = engine.get_legal_actions(state)
        hero_attacks = [a for a in actions
                        if hasattr(a, 'attacker_idx') and a.attacker_idx == -1]
        assert len(hero_attacks) == 0


class TestCantAttack:
    def test_cant_attack_prevents_attack(self):
        m = MinionState(
            card_id="a", name="Ancient Watcher", attack=4, health=5, max_health=5,
            mana_cost=2, mechanics=["CANT_ATTACK"], summoned_this_turn=False,
        )
        assert m.can_attack is False


class TestStealth:
    def test_stealth_removed_on_minion_attack(self):
        engine = GameEngine()
        state = _make_game()
        attacker = MinionState(
            card_id="a", name="Stealthy", attack=3, health=2, max_health=2,
            mana_cost=2, stealth=True, summoned_this_turn=False,
        )
        defender = MinionState(
            card_id="b", name="Target", attack=1, health=5, max_health=5,
            mana_cost=2,
        )
        state.player1.board.append(attacker)
        state.player2.board.append(defender)
        assert attacker.stealth is True
        engine.resolve_combat(attacker, defender, state=state)
        assert attacker.stealth is False
