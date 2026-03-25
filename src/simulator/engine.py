from __future__ import annotations
import logging
import random
from typing import TYPE_CHECKING
from src.simulator.game_state import GameState, MinionState, PlayerState, HeroState, WeaponState

if TYPE_CHECKING:
    from src.simulator.actions import PlayCard, Attack

logger = logging.getLogger(__name__)
MAX_MANA = 10
STARTING_HAND_FIRST = 3
STARTING_HAND_SECOND = 4


class GameEngine:
    def __init__(self, card_db: dict | None = None):
        self.card_db = card_db or {}

    def start_game(self, state: GameState):
        random.shuffle(state.player1.deck)
        random.shuffle(state.player2.deck)
        for _ in range(STARTING_HAND_FIRST):
            state.player1.draw_card()
        for _ in range(STARTING_HAND_SECOND):
            state.player2.draw_card()

    def start_turn(self, state: GameState):
        player = state.current_player
        player.max_mana = min(player.max_mana + 1, MAX_MANA)
        player.mana = player.max_mana - player.overload
        player.overload = 0
        player.hero.hero_power_used = False
        player.hero.attack = 0
        player.draw_card()

    def end_turn(self, state: GameState):
        player = state.current_player
        for m in player.board:
            m.attacks_this_turn = 0
            m.summoned_this_turn = False
            if m.frozen:
                m.frozen = False
        state.switch_turn()

    def resolve_combat(self, attacker: MinionState, defender: MinionState):
        defender.take_damage(attacker.attack)
        attacker.take_damage(defender.attack)
        attacker.attacks_this_turn += 1

    def attack_hero(self, attacker: MinionState, hero: HeroState):
        hero.take_damage(attacker.attack)
        attacker.attacks_this_turn += 1
        if attacker.stealth:
            attacker.stealth = False

    def hero_attack_minion(self, state: GameState, target: MinionState):
        player = state.current_player
        attack = player.hero.total_attack
        target.take_damage(attack)
        player.hero.take_damage(target.attack)
        player.hero.attack = 0
        if player.hero.weapon and not player.hero.weapon.is_broken:
            player.hero.weapon.durability -= 1
            if player.hero.weapon.is_broken:
                player.hero.weapon = None

    def hero_attack_hero(self, state: GameState):
        player = state.current_player
        opponent = state.opponent
        attack = player.hero.total_attack
        opponent.hero.take_damage(attack)
        player.hero.attack = 0
        if player.hero.weapon and not player.hero.weapon.is_broken:
            player.hero.weapon.durability -= 1
            if player.hero.weapon.is_broken:
                player.hero.weapon = None

    def remove_dead_minions(self, state: GameState):
        state.player1.board = [m for m in state.player1.board if not m.is_dead]
        state.player2.board = [m for m in state.player2.board if not m.is_dead]

    def play_minion(self, state: GameState, card_data: dict) -> MinionState | None:
        player = state.current_player
        if player.board_full:
            return None
        mechanics = card_data.get("mechanics", [])
        minion = MinionState(
            card_id=card_data.get("card_id", ""), name=card_data.get("name", ""),
            attack=card_data.get("attack", 0), health=card_data.get("health", 1),
            max_health=card_data.get("health", 1), mana_cost=card_data.get("mana_cost", 0),
            taunt="TAUNT" in mechanics, divine_shield="DIVINE_SHIELD" in mechanics,
            stealth="STEALTH" in mechanics, windfury="WINDFURY" in mechanics,
            lifesteal="LIFESTEAL" in mechanics, poisonous="POISONOUS" in mechanics,
            reborn="REBORN" in mechanics, rush="RUSH" in mechanics,
            charge="CHARGE" in mechanics, mechanics=mechanics,
        )
        player.board.append(minion)
        player.mana -= card_data.get("mana_cost", 0)
        return minion

    def play_spell(self, state: GameState, card_data: dict, target=None):
        player = state.current_player
        player.mana -= card_data.get("mana_cost", 0)

    def use_hero_power(self, state: GameState, target=None):
        player = state.current_player
        if player.hero.hero_power_used or player.mana < player.hero.hero_power_cost:
            return
        player.mana -= player.hero.hero_power_cost
        player.hero.hero_power_used = True
        hero_class = player.hero.hero_class
        opponent = state.opponent

        if hero_class == "MAGE":
            if target and isinstance(target, MinionState):
                target.take_damage(1)
            else:
                opponent.hero.take_damage(1)
        elif hero_class == "WARRIOR":
            player.hero.armor += 2
        elif hero_class == "PRIEST":
            if target and isinstance(target, MinionState):
                target.health = min(target.health + 2, target.max_health)
            else:
                player.hero.health = min(player.hero.health + 2, player.hero.max_health)
        elif hero_class == "HUNTER":
            opponent.hero.take_damage(2)
        elif hero_class == "PALADIN":
            if not player.board_full:
                player.board.append(MinionState(card_id="CS2_101t", name="Silver Hand Recruit",
                    attack=1, health=1, max_health=1, mana_cost=0))
        elif hero_class == "WARLOCK":
            player.hero.take_damage(2)
            player.draw_card()
        elif hero_class == "ROGUE":
            player.hero.weapon = WeaponState(card_id="CS2_082", name="Wicked Knife", attack=1, durability=2)
        elif hero_class == "SHAMAN":
            if not player.board_full:
                totems = [
                    MinionState(card_id="t1", name="Healing Totem", attack=0, health=2, max_health=2, mana_cost=0),
                    MinionState(card_id="t2", name="Searing Totem", attack=1, health=1, max_health=1, mana_cost=0),
                    MinionState(card_id="t3", name="Stoneclaw Totem", attack=0, health=2, max_health=2, mana_cost=0, taunt=True),
                    MinionState(card_id="t4", name="Wrath of Air Totem", attack=0, health=2, max_health=2, mana_cost=0),
                ]
                player.board.append(random.choice(totems))
        elif hero_class == "DRUID":
            player.hero.armor += 1
            player.hero.attack += 1
        elif hero_class == "DEMON_HUNTER":
            player.hero.attack += 1
        elif hero_class == "DEATH_KNIGHT":
            if not player.board_full:
                player.board.append(MinionState(card_id="dk_ghoul", name="Ghoul",
                    attack=1, health=1, max_health=1, mana_cost=0))

    def get_legal_actions(self, state: GameState) -> list:
        from src.simulator.actions import PlayCard, Attack, HeroPower, EndTurn
        actions = []
        player = state.current_player
        opponent = state.opponent

        for i, card_id in enumerate(player.hand):
            card_data = self.card_db.get(card_id)
            if card_data and card_data.get("mana_cost", 99) <= player.mana:
                if card_data.get("card_type", "") == "MINION" and player.board_full:
                    continue
                actions.append(PlayCard(card_id=card_id, hand_idx=i))

        has_taunt = any(m.taunt for m in opponent.board)
        for i, m in enumerate(player.board):
            if not m.can_attack:
                continue
            if m.can_attack_minions:
                for j, target in enumerate(opponent.board):
                    if has_taunt and not target.taunt:
                        continue
                    if target.stealth:
                        continue
                    actions.append(Attack(attacker_idx=i, target_idx=j))
            if m.can_attack_hero and not has_taunt:
                actions.append(Attack(attacker_idx=i, target_idx=-1, target_is_hero=True))

        # Hero attack with weapon/attack
        if player.hero.total_attack > 0:
            for j, target in enumerate(opponent.board):
                if has_taunt and not target.taunt:
                    continue
                if target.stealth:
                    continue
                actions.append(Attack(attacker_idx=-1, target_idx=j))
            if not has_taunt:
                actions.append(Attack(attacker_idx=-1, target_idx=-1, target_is_hero=True))

        if not player.hero.hero_power_used and player.mana >= player.hero.hero_power_cost:
            actions.append(HeroPower())

        actions.append(EndTurn())
        return actions
