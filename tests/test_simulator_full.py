"""Comprehensive simulator verification — all implemented mechanics."""
import pytest
from src.simulator.game_state import (
    GameState, MinionState, PlayerState, HeroState, WeaponState, BOARD_LIMIT
)
from src.simulator.engine import GameEngine
from src.simulator.actions import Attack, PlayCard, EndTurn, HeroPower


def _state(hero_a="MAGE", hero_b="WARRIOR", **kw):
    return GameState(
        player1=PlayerState(hero=HeroState(hero_a), **kw),
        player2=PlayerState(hero=HeroState(hero_b)),
    )


class TestTaunt:
    def test_taunt_blocks_non_taunt(self):
        engine = GameEngine()
        state = _state()
        state.player2.board = [
            MinionState("t", "Taunt", 2, 5, 5, 3, taunt=True),
            MinionState("n", "Normal", 3, 3, 3, 2),
        ]
        state.player1.board = [
            MinionState("a", "Atk", 4, 4, 4, 3, summoned_this_turn=False),
        ]
        actions = engine.get_legal_actions(state)
        atk_actions = [a for a in actions if isinstance(a, Attack) and a.attacker_idx == 0]
        targets = [a.target_idx for a in atk_actions if not a.target_is_hero]
        assert 0 in targets  # taunt
        assert 1 not in targets  # normal blocked
        assert not any(a.target_is_hero for a in atk_actions)  # hero blocked


class TestDivineShield:
    def test_absorbs_damage(self):
        m = MinionState("d", "Shield", 3, 4, 4, 3, divine_shield=True)
        m.take_damage(5)
        assert m.health == 4
        assert m.divine_shield is False

    def test_takes_damage_after_broken(self):
        m = MinionState("d", "Shield", 3, 4, 4, 3, divine_shield=True)
        m.take_damage(1)
        m.take_damage(2)
        assert m.health == 2


class TestCharge:
    def test_can_attack_on_summon(self):
        m = MinionState("c", "Charger", 4, 3, 3, 3, charge=True, summoned_this_turn=True)
        assert m.can_attack is True
        assert m.can_attack_hero is True


class TestRush:
    def test_can_attack_minions_not_hero(self):
        m = MinionState("r", "Rusher", 3, 3, 3, 3, rush=True, summoned_this_turn=True)
        assert m.can_attack_minions is True
        assert m.can_attack_hero is False


class TestWindfury:
    def test_attacks_twice(self):
        m = MinionState("w", "Windy", 3, 3, 3, 3, windfury=True, summoned_this_turn=False)
        m.attacks_this_turn = 1
        assert m.can_attack is True
        m.attacks_this_turn = 2
        assert m.can_attack is False


class TestStealth:
    def test_cannot_be_targeted(self):
        engine = GameEngine()
        state = _state()
        stealthy = MinionState("s", "Stealth", 3, 3, 3, 2, stealth=True)
        state.player2.board = [stealthy]
        state.player1.board = [MinionState("a", "Atk", 2, 4, 4, 2, summoned_this_turn=False)]
        actions = engine.get_legal_actions(state)
        minion_attacks = [a for a in actions if isinstance(a, Attack)
                         and a.attacker_idx == 0 and not a.target_is_hero]
        assert len(minion_attacks) == 0

    def test_removed_on_attack(self):
        engine = GameEngine()
        state = _state()
        stealthy = MinionState("s", "Stealth", 3, 3, 3, 2, stealth=True, summoned_this_turn=False)
        defender = MinionState("d", "Def", 2, 5, 5, 2)
        state.player1.board = [stealthy]
        state.player2.board = [defender]
        engine.resolve_combat(stealthy, defender, state)
        assert stealthy.stealth is False


class TestFreeze:
    def test_frozen_cannot_attack(self):
        m = MinionState("f", "Frozen", 3, 5, 5, 2, frozen=True, summoned_this_turn=False)
        assert m.can_attack is False

    def test_thaw_after_skip(self):
        engine = GameEngine()
        state = _state()
        m = MinionState("f", "Frozen", 3, 5, 5, 2, frozen=True, summoned_this_turn=False)
        state.player1.board = [m]
        engine.end_turn(state)
        assert m.frozen is False

    def test_stay_frozen_if_attacked(self):
        engine = GameEngine()
        state = _state()
        m = MinionState("a", "Attacker", 3, 5, 5, 2, summoned_this_turn=False)
        freezer = MinionState("b", "Freezer", 2, 3, 3, 1, mechanics=["FREEZE"])
        state.player1.board = [m]
        state.player2.board = [freezer]
        engine.resolve_combat(m, freezer, state)
        assert m.frozen is True
        engine.end_turn(state)
        assert m.frozen is True  # attacked this turn, stays frozen


class TestPoisonous:
    def test_kills_any_minion(self):
        engine = GameEngine()
        attacker = MinionState("p", "Poison", 1, 1, 1, 1, poisonous=True)
        defender = MinionState("d", "BigGuy", 1, 100, 100, 10)
        engine.resolve_combat(attacker, defender)
        assert defender.health <= 0


class TestLifesteal:
    def test_heals_hero(self):
        engine = GameEngine()
        state = _state()
        state.player1.hero.health = 20
        ls = MinionState("l", "Lifesteal", 5, 5, 5, 3, lifesteal=True, summoned_this_turn=False)
        target = MinionState("t", "Target", 0, 10, 10, 5)
        state.player1.board = [ls]
        state.player2.board = [target]
        engine.resolve_combat(ls, target, state)
        assert state.player1.hero.health == 25


class TestReborn:
    def test_respawns_with_1_health(self):
        engine = GameEngine()
        state = _state()
        reborn = MinionState("r", "Reborn", 3, 3, 3, 3, reborn=True)
        state.player1.board = [reborn]
        reborn.health = 0
        engine.remove_dead_minions(state)
        assert len(state.player1.board) == 1
        assert state.player1.board[0].health == 1
        assert state.player1.board[0].reborn is False


class TestBattlecry:
    def test_deals_damage(self):
        engine = GameEngine({"bc": {"text": "전투의 함성: 피해를 3 줍니다", "mechanics": ["BATTLECRY"]}})
        state = _state(mana=5, max_mana=5)
        engine.play_minion(state, {"card_id": "bc", "name": "BC", "attack": 2, "health": 2,
            "mana_cost": 2, "mechanics": ["BATTLECRY"], "text": "전투의 함성: 피해를 3 줍니다"})
        assert state.player2.hero.health == 27


class TestDeathrattle:
    def test_draws_cards(self):
        engine = GameEngine({"dr": {"text": "죽음의 메아리: 카드를 2장 뽑습니다", "mechanics": ["DEATHRATTLE"]}})
        state = _state(deck=["c1", "c2", "c3"])
        dr = MinionState("dr", "DR", 1, 0, 2, 1, mechanics=["DEATHRATTLE"])
        state.player1.board = [dr]
        engine.remove_dead_minions(state)
        assert len(state.player1.hand) == 2


class TestCombo:
    def test_buffs_with_prior_cards(self):
        engine = GameEngine()
        state = _state(mana=10, max_mana=10)
        state.player1.cards_played_this_turn = 1
        m = engine.play_minion(state, {"card_id": "cb", "name": "Combo", "attack": 2, "health": 2,
            "mana_cost": 2, "mechanics": ["COMBO"], "text": "연계: +2/+2"})
        assert m.attack == 4
        assert m.health == 4


class TestEcho:
    def test_adds_copy_to_hand(self):
        engine = GameEngine()
        state = _state(mana=10, max_mana=10)
        engine.play_minion(state, {"card_id": "echo1", "name": "Echo", "attack": 1, "health": 1,
            "mana_cost": 1, "mechanics": ["ECHO"]})
        assert "echo1" in state.player1.hand

    def test_removed_at_end_turn(self):
        engine = GameEngine()
        state = _state(mana=10, max_mana=10)
        engine.play_minion(state, {"card_id": "echo1", "name": "Echo", "attack": 1, "health": 1,
            "mana_cost": 1, "mechanics": ["ECHO"]})
        engine.end_turn(state)
        # After end_turn, switch happens. Echo cards cleared for p1.
        assert "echo1" not in state.player1.hand


class TestOverload:
    def test_reduces_next_turn_mana(self):
        engine = GameEngine()
        state = _state(mana=5, max_mana=5)
        engine.play_minion(state, {"card_id": "ol", "name": "OL", "attack": 4, "health": 4,
            "mana_cost": 3, "mechanics": [], "overload": 2})
        assert state.player1.overload == 2


class TestSpellPower:
    def test_adds_to_spell_damage(self):
        engine = GameEngine()
        state = _state(mana=10, max_mana=10)
        sp = MinionState("sp", "SpellDmg", 1, 3, 3, 2, mechanics=["SPELLPOWER"])
        state.player1.board = [sp]
        engine.play_spell(state, {"mana_cost": 2, "text": "적 영웅에게 피해를 3 줍니다", "mechanics": []})
        assert state.player2.hero.health == 26  # 3+1=4


class TestFrenzy:
    def test_triggers_on_first_damage(self):
        engine = GameEngine({"fr": {"text": "광란: +3/+3", "mechanics": ["FRENZY"]}})
        state = _state()
        fr = MinionState("fr", "Frenzy", 2, 5, 5, 3, mechanics=["FRENZY"])
        enemy = MinionState("e", "Enemy", 1, 3, 3, 1)
        state.player1.board = [fr]
        state.player2.board = [enemy]
        engine.resolve_combat(fr, enemy, state)
        assert fr.attack == 5
        assert fr.frenzy_triggered is True

    def test_only_triggers_once(self):
        engine = GameEngine({"fr": {"text": "광란: +3/+3", "mechanics": ["FRENZY"]}})
        state = _state()
        fr = MinionState("fr", "Frenzy", 2, 10, 10, 3, mechanics=["FRENZY"])
        enemy = MinionState("e", "Enemy", 1, 10, 10, 1)
        state.player1.board = [fr]
        state.player2.board = [enemy]
        engine.resolve_combat(fr, enemy, state)
        old_atk = fr.attack
        engine.resolve_combat(fr, enemy, state)
        assert fr.attack == old_atk


class TestSpellburst:
    def test_triggers_on_spell(self):
        engine = GameEngine({"sb": {"text": "주문폭발: +2/+2", "mechanics": ["SPELLBURST"]}})
        state = _state(mana=10, max_mana=10)
        sb = MinionState("sb", "SB", 2, 3, 3, 2, mechanics=["SPELLBURST"], spellburst_active=True)
        state.player1.board = [sb]
        engine.play_spell(state, {"mana_cost": 1, "text": "적 영웅에게 피해를 1 줍니다", "mechanics": []})
        assert sb.attack == 4
        assert sb.spellburst_active is False


class TestOutcast:
    def test_triggers_from_leftmost(self):
        engine = GameEngine({"oc": {"text": "추방자: 카드를 1장 뽑습니다", "mechanics": ["OUTCAST"]}})
        state = _state(mana=5, max_mana=5, deck=["d1", "d2"])
        state.player1.hand = ["oc", "x", "y"]
        # Simulate what _execute_action does: pop from hand first, then play_minion
        state.player1.hand.pop(0)  # remove "oc" from hand
        engine.play_minion(state, {"card_id": "oc", "name": "OC", "attack": 2, "health": 2,
            "mana_cost": 2, "mechanics": ["OUTCAST"], "text": "추방자: 카드를 1장 뽑습니다"},
            hand_position=0)
        # hand was [x, y], outcast drew 1 card -> [x, y, d1]
        assert len(state.player1.hand) == 3


class TestElusive:
    def test_hero_power_redirects(self):
        engine = GameEngine()
        state = _state(mana=5, max_mana=5)
        elusive = MinionState("e", "Elusive", 4, 5, 5, 3, mechanics=["ELUSIVE"])
        state.player2.board = [elusive]
        engine.use_hero_power(state, target=elusive)
        assert elusive.health == 5
        assert state.player2.hero.health == 29

    def test_spell_skips_elusive(self):
        engine = GameEngine()
        state = _state(mana=10, max_mana=10)
        elusive = MinionState("e", "Elusive", 4, 5, 5, 3, mechanics=["ELUSIVE"])
        normal = MinionState("n", "Normal", 2, 3, 3, 2)
        state.player2.board = [elusive, normal]
        engine.play_spell(state, {"mana_cost": 2, "text": "하수인 하나에게 피해를 3 줍니다", "mechanics": []},
                          target=elusive)
        assert elusive.health == 5
        assert normal.health == 0


class TestSilence:
    def test_removes_all_enchantments(self):
        engine = GameEngine()
        m = MinionState("s", "Silenced", 3, 5, 5, 3, taunt=True, divine_shield=True,
            reborn=True, lifesteal=True, mechanics=["TAUNT", "DIVINE_SHIELD", "REBORN", "LIFESTEAL"])
        engine.silence_minion(m)
        assert m.taunt is False
        assert m.divine_shield is False
        assert m.reborn is False
        assert m.mechanics == []


class TestAura:
    def test_buffs_others(self):
        engine = GameEngine({"aura1": {"text": "다른 아군 하수인에게 +2 공격력을 부여합니다", "mechanics": ["AURA"]}})
        state = _state()
        aura = MinionState("aura1", "Aura", 1, 3, 3, 2, mechanics=["AURA"])
        buddy = MinionState("b", "Buddy", 3, 5, 5, 3)
        state.player1.board = [aura, buddy]
        engine.apply_auras(state)
        assert buddy.attack == 5
        assert aura.attack == 1


class TestSecret:
    def test_stored_on_play(self):
        engine = GameEngine()
        state = _state(mana=5, max_mana=5)
        engine.play_spell(state, {"card_id": "trap", "mana_cost": 2,
            "text": "secret text", "mechanics": ["SECRET"]})
        assert len(state.player1.secrets) == 1

    def test_triggers_on_hero_attack(self):
        engine = GameEngine({"trap": {"text": "적 하수인이 공격하면 영웅에게", "mechanics": ["SECRET"]}})
        state = _state()
        state.player2.secrets = ["trap"]
        attacker = MinionState("a", "Atk", 5, 4, 4, 3)
        state.player1.board = [attacker]
        engine.attack_hero(attacker, state.player2.hero, state=state)
        assert attacker.health == 2
        assert len(state.player2.secrets) == 0


class TestFriendlyDeaths:
    def test_counter_increments(self):
        engine = GameEngine()
        state = _state()
        dead1 = MinionState("d1", "Dead1", 1, 0, 2, 1)
        dead2 = MinionState("d2", "Dead2", 1, 0, 2, 1)
        alive = MinionState("a", "Alive", 2, 3, 3, 2)
        state.player1.board = [dead1, dead2, alive]
        engine.remove_dead_minions(state)
        assert state.player1.friendly_deaths_this_game == 2
        assert len(state.player1.board) == 1


class TestHeroPowers:
    @pytest.mark.parametrize("hero_class", [
        "MAGE", "WARRIOR", "PRIEST", "HUNTER", "PALADIN",
        "WARLOCK", "ROGUE", "SHAMAN", "DRUID", "DEMON_HUNTER", "DEATH_KNIGHT",
    ])
    def test_hero_power(self, hero_class):
        engine = GameEngine()
        state = _state(hero_a=hero_class, mana=5, max_mana=5, deck=["c1", "c2"])
        engine.use_hero_power(state)
        assert state.player1.hero.hero_power_used is True


class TestMatchSimulation:
    def test_match_completes(self):
        from src.simulator.match import run_match
        card_db = {
            f"c_{i}": {
                "card_id": f"c_{i}", "card_type": "MINION",
                "mana_cost": (i % 7) + 1, "attack": (i % 5) + 1,
                "health": (i % 5) + 2, "mechanics": [], "name": f"Card {i}",
            }
            for i in range(30)
        }
        deck = [f"c_{i}" for i in range(15)] * 2
        result = run_match(list(deck), list(deck), "MAGE", "WARRIOR", card_db, max_turns=60)
        assert result.turns > 0
        assert result.winner in ("A", "B", None)

    def test_bulk_matches(self):
        from src.simulator.match import run_match
        card_db = {
            f"c_{i}": {
                "card_id": f"c_{i}", "card_type": "MINION",
                "mana_cost": (i % 7) + 1, "attack": (i % 5) + 1,
                "health": (i % 5) + 2, "mechanics": [], "name": f"Card {i}",
            }
            for i in range(30)
        }
        deck = [f"c_{i}" for i in range(15)] * 2
        wins = {"A": 0, "B": 0, "draw": 0}
        for _ in range(10):
            r = run_match(list(deck), list(deck), "MAGE", "WARRIOR", card_db, max_turns=60)
            if r.winner == "A":
                wins["A"] += 1
            elif r.winner == "B":
                wins["B"] += 1
            else:
                wins["draw"] += 1
        total = wins["A"] + wins["B"] + wins["draw"]
        assert total == 10
