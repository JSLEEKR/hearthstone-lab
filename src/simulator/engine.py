from __future__ import annotations
import logging
import random
from typing import TYPE_CHECKING
from src.simulator.game_state import GameState, MinionState, PlayerState, HeroState, WeaponState, BOARD_LIMIT

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
        player.hero.attacks_this_turn = 0
        player.draw_card()

    def end_turn(self, state: GameState):
        player = state.current_player
        for m in player.board:
            m.attacks_this_turn = 0
            m.summoned_this_turn = False
            if m.frozen:
                m.frozen = False
        player.hero.attack = 0
        player.hero.attacks_this_turn = 0
        state.switch_turn()

    def resolve_combat(self, attacker: MinionState, defender: MinionState,
                       state: GameState | None = None):
        # FORGETFUL: 50% chance to attack a random other target
        if "FORGETFUL" in attacker.mechanics and state is not None:
            if random.random() < 0.5:
                opponent = state.opponent
                other_targets = [m for m in opponent.board if m is not defender]
                if not defender.is_dead:
                    other_targets.append(opponent.hero)
                if other_targets:
                    new_target = random.choice(other_targets)
                    if isinstance(new_target, HeroState):
                        self.attack_hero(attacker, new_target, state=state)
                        return
                    else:
                        defender = new_target

        # STEALTH removal on any attack
        if attacker.stealth:
            attacker.stealth = False

        damage_to_defender = defender.take_damage(attacker.attack)
        damage_to_attacker = attacker.take_damage(defender.attack)
        attacker.attacks_this_turn += 1

        # POISONOUS
        if attacker.poisonous and damage_to_defender > 0:
            defender.health = 0
        if defender.poisonous and damage_to_attacker > 0:
            attacker.health = 0

        # LIFESTEAL
        if attacker.lifesteal and damage_to_defender > 0 and state is not None:
            hero = state.current_player.hero
            hero.health = min(hero.health + damage_to_defender, hero.max_health)

        # FREEZE
        if "FREEZE" in attacker.mechanics:
            defender.frozen = True
        if "FREEZE" in defender.mechanics:
            attacker.frozen = True

        # ENRAGE
        if state is not None:
            self.apply_enrage(state)

    def attack_hero(self, attacker: MinionState, hero: HeroState,
                    state: GameState | None = None):
        damage_dealt = hero.take_damage(attacker.attack)
        attacker.attacks_this_turn += 1
        if attacker.stealth:
            attacker.stealth = False

        # LIFESTEAL
        if attacker.lifesteal and damage_dealt > 0 and state is not None:
            owner_hero = state.current_player.hero
            owner_hero.health = min(owner_hero.health + damage_dealt, owner_hero.max_health)

    def hero_attack_minion(self, state: GameState, target: MinionState):
        player = state.current_player
        attack = player.hero.total_attack
        target.take_damage(attack)
        player.hero.take_damage(target.attack)
        player.hero.attacks_this_turn += 1
        if player.hero.weapon and not player.hero.weapon.is_broken:
            player.hero.weapon.durability -= 1
            if player.hero.weapon.is_broken:
                player.hero.weapon = None

    def hero_attack_hero(self, state: GameState):
        player = state.current_player
        opponent = state.opponent
        attack = player.hero.total_attack
        opponent.hero.take_damage(attack)
        player.hero.attacks_this_turn += 1
        if player.hero.weapon and not player.hero.weapon.is_broken:
            player.hero.weapon.durability -= 1
            if player.hero.weapon.is_broken:
                player.hero.weapon = None

    def remove_dead_minions(self, state: GameState):
        # Process deathrattles for dead minions before removal
        from src.simulator.spell_parser import parse_deathrattle_effects
        for player_idx, player in enumerate([state.player1, state.player2]):
            opponent = state.player2 if player_idx == 0 else state.player1
            for m in player.board:
                if m.is_dead and "DEATHRATTLE" in m.mechanics:
                    effects = parse_deathrattle_effects(self.card_db.get(m.card_id, {}).get("text", ""))
                    for eff in effects:
                        if eff.effect_type == "damage":
                            if opponent.board:
                                import random as _rand
                                t = _rand.choice(opponent.board)
                                t.take_damage(eff.value)
                        elif eff.effect_type == "draw":
                            for _ in range(eff.value):
                                player.draw_card()
                        elif eff.effect_type == "summon" and not player.board_full:
                            player.board.append(MinionState(
                                card_id="token", name="Token",
                                attack=eff.value, health=eff.value2, max_health=eff.value2,
                                mana_cost=0,
                            ))

        for player in (state.player1, state.player2):
            new_board: list[MinionState] = []
            for m in player.board:
                if m.is_dead:
                    # REBORN: respawn with 1 health at same position
                    if m.reborn and len(new_board) < BOARD_LIMIT:
                        reborn_copy = MinionState(
                            card_id=m.card_id, name=m.name,
                            attack=m.attack - m.enrage_bonus, health=1, max_health=1,
                            mana_cost=m.mana_cost, taunt=m.taunt,
                            divine_shield=False, stealth=m.stealth,
                            windfury=m.windfury, lifesteal=m.lifesteal,
                            poisonous=m.poisonous, reborn=False,
                            rush=m.rush, charge=m.charge,
                            mechanics=list(m.mechanics),
                            summoned_this_turn=True,
                        )
                        new_board.append(reborn_copy)
                else:
                    new_board.append(m)
            player.board = new_board

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
        # OVERLOAD
        overload = card_data.get("overload", 0)
        if overload:
            player.overload += overload

        # Apply battlecry
        if "BATTLECRY" in mechanics:
            from src.simulator.spell_parser import parse_battlecry_effects
            effects = parse_battlecry_effects(card_data.get("text", ""))
            for eff in effects:
                if eff.effect_type == "damage":
                    if eff.target == "enemy_hero":
                        state.opponent.hero.take_damage(eff.value)
                    elif state.opponent.board:
                        t = max(state.opponent.board, key=lambda m: m.health)
                        t.take_damage(eff.value)
                elif eff.effect_type == "aoe_damage":
                    if eff.target == "all_enemy_minions":
                        for m in state.opponent.board:
                            m.take_damage(eff.value)
                    elif eff.target == "all_minions":
                        for m in state.current_player.board + state.opponent.board:
                            if m is not minion:
                                m.take_damage(eff.value)
                elif eff.effect_type == "draw":
                    for _ in range(eff.value):
                        player.draw_card()
                elif eff.effect_type == "buff":
                    minion.attack += eff.value
                    minion.health += eff.value2
                    minion.max_health += eff.value2
                elif eff.effect_type == "heal":
                    player.hero.health = min(player.hero.health + eff.value, player.hero.max_health)
                elif eff.effect_type == "armor":
                    player.hero.armor += eff.value

        return minion

    def play_spell(self, state: GameState, card_data: dict, target=None):
        player = state.current_player
        opponent = state.opponent
        player.mana -= card_data.get("mana_cost", 0)
        # OVERLOAD
        overload = card_data.get("overload", 0)
        if overload:
            player.overload += overload

        from src.simulator.spell_parser import parse_spell_effects
        effects = parse_spell_effects(card_data.get("text", ""))

        for eff in effects:
            if eff.effect_type == "damage":
                if eff.target == "enemy_hero":
                    opponent.hero.take_damage(eff.value)
                elif eff.target == "enemy_minion" and opponent.board:
                    t = max(opponent.board, key=lambda m: m.health) if not target else target
                    t.take_damage(eff.value)
                elif eff.target == "auto":
                    opponent.hero.take_damage(eff.value)

            elif eff.effect_type == "aoe_damage":
                if eff.target == "all_minions":
                    for m in player.board + opponent.board:
                        m.take_damage(eff.value)
                elif eff.target == "all_enemy_minions":
                    for m in opponent.board:
                        m.take_damage(eff.value)

            elif eff.effect_type == "heal":
                if eff.target == "auto" or eff.target == "self_hero":
                    player.hero.health = min(player.hero.health + eff.value, player.hero.max_health)

            elif eff.effect_type == "draw":
                for _ in range(eff.value):
                    player.draw_card()

            elif eff.effect_type == "buff" and player.board:
                t = player.board[-1] if player.board else None
                if t:
                    t.attack += eff.value
                    t.health += eff.value2
                    t.max_health += eff.value2

            elif eff.effect_type == "armor":
                player.hero.armor += eff.value

            elif eff.effect_type == "destroy" and opponent.board:
                t = max(opponent.board, key=lambda m: m.health)
                t.health = 0

            elif eff.effect_type == "freeze_all":
                for m in opponent.board:
                    m.frozen = True

            elif eff.effect_type == "summon" and not player.board_full:
                player.board.append(MinionState(
                    card_id="token", name="Token",
                    attack=eff.value, health=eff.value2, max_health=eff.value2,
                    mana_cost=0,
                ))

        self.remove_dead_minions(state)

    def apply_enrage(self, state: GameState):
        """Check all minions for enrage status and apply/remove bonus."""
        for player in (state.player1, state.player2):
            for m in player.board:
                if "ENRAGED" in m.mechanics:
                    if m.health < m.max_health and m.enrage_bonus == 0:
                        m.enrage_bonus = 2
                        m.attack += 2
                    elif m.health >= m.max_health and m.enrage_bonus > 0:
                        m.attack -= m.enrage_bonus
                        m.enrage_bonus = 0

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
        if player.hero.total_attack > 0 and player.hero.attacks_this_turn == 0:
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
