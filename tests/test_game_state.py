import pytest
from src.simulator.game_state import (
    MinionState, WeaponState, PlayerState, GameState, HeroState,
)


class TestMinionState:
    def test_create_minion(self):
        m = MinionState(card_id="CS2_182", name="Chillwind Yeti",
                        attack=4, health=5, max_health=5, mana_cost=4)
        assert m.attack == 4
        assert m.health == 5
        assert m.can_attack is False

    def test_minion_take_damage(self):
        m = MinionState(card_id="CS2_182", name="Yeti", attack=4, health=5, max_health=5, mana_cost=4)
        m.take_damage(3)
        assert m.health == 2
        assert m.is_dead is False

    def test_minion_dies_at_zero(self):
        m = MinionState(card_id="CS2_182", name="Yeti", attack=4, health=5, max_health=5, mana_cost=4)
        m.take_damage(5)
        assert m.is_dead is True

    def test_minion_with_taunt(self):
        m = MinionState(card_id="CS2_125", name="Sen'jin", attack=3, health=5, max_health=5, mana_cost=4, taunt=True)
        assert m.taunt is True

    def test_minion_with_rush_can_attack_minions(self):
        m = MinionState(card_id="TEST", name="Rusher", attack=3, health=3, max_health=3, mana_cost=3, rush=True)
        assert m.can_attack_minions is True
        assert m.can_attack_hero is False

    def test_minion_with_charge(self):
        m = MinionState(card_id="TEST", name="Charger", attack=4, health=2, max_health=2, mana_cost=4, charge=True)
        assert m.can_attack is True


class TestHeroState:
    def test_default_hero(self):
        h = HeroState(hero_class="MAGE")
        assert h.health == 30
        assert h.armor == 0

    def test_hero_take_damage_with_armor(self):
        h = HeroState(hero_class="WARRIOR", armor=5)
        h.take_damage(7)
        assert h.armor == 0
        assert h.health == 28


class TestPlayerState:
    def test_initial_state(self):
        p = PlayerState(hero=HeroState(hero_class="MAGE"))
        assert p.mana == 0
        assert len(p.hand) == 0

    def test_draw_from_deck(self):
        p = PlayerState(hero=HeroState(hero_class="MAGE"))
        p.deck = ["card1", "card2", "card3"]
        drawn = p.draw_card()
        assert drawn == "card1"
        assert len(p.deck) == 2

    def test_draw_fatigue(self):
        p = PlayerState(hero=HeroState(hero_class="MAGE"))
        p.deck = []
        drawn = p.draw_card()
        assert drawn is None
        assert p.fatigue_counter == 1
        assert p.hero.health == 29

    def test_hand_limit_burn(self):
        p = PlayerState(hero=HeroState(hero_class="MAGE"))
        p.hand = [f"c{i}" for i in range(10)]
        p.deck = ["overflow"]
        drawn = p.draw_card()
        assert drawn is None
        assert len(p.hand) == 10

    def test_board_full(self):
        p = PlayerState(hero=HeroState(hero_class="MAGE"))
        for i in range(7):
            p.board.append(MinionState(card_id=f"m{i}", name=f"m{i}", attack=1, health=1, max_health=1, mana_cost=1))
        assert p.board_full is True


class TestGameState:
    def test_create_game(self):
        g = GameState(
            player1=PlayerState(hero=HeroState(hero_class="MAGE")),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        assert g.turn == 0
        assert g.game_over is False

    def test_switch_turn(self):
        g = GameState(
            player1=PlayerState(hero=HeroState(hero_class="MAGE")),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        g.switch_turn()
        assert g.current_player_idx == 1
        assert g.turn == 1

    def test_game_over_when_hero_dies(self):
        g = GameState(
            player1=PlayerState(hero=HeroState(hero_class="MAGE")),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        g.player1.hero.health = 0
        assert g.game_over is True
        assert g.winner_idx == 1
