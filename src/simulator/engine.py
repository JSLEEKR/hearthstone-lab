from __future__ import annotations
import logging
import random
import re
from typing import TYPE_CHECKING
from src.simulator.game_state import GameState, MinionState, PlayerState, HeroState, WeaponState, BOARD_LIMIT

if TYPE_CHECKING:
    from src.simulator.actions import PlayCard, Attack, TradeCard

logger = logging.getLogger(__name__)
MAX_MANA = 10
STARTING_HAND_FIRST = 3
STARTING_HAND_SECOND = 4


class GameEngine:
    def __init__(self, card_db: dict | None = None):
        self.card_db = card_db or {}

    def _can_be_targeted(self, minion: MinionState) -> bool:
        """Return False if the minion has ELUSIVE and cannot be targeted by spells/hero powers."""
        return "ELUSIVE" not in minion.mechanics

    def silence_minion(self, minion: MinionState):
        """Remove all enchantments from a minion."""
        minion.taunt = False
        minion.divine_shield = False
        minion.stealth = False
        minion.windfury = False
        minion.lifesteal = False
        minion.poisonous = False
        minion.reborn = False
        minion.rush = False
        minion.charge = False
        minion.frozen = False
        minion.enrage_bonus = 0
        minion.aura_attack_bonus = 0
        minion.mechanics = []

    def apply_auras(self, state: GameState):
        """Apply simple aura effects. Called after board changes."""
        for player in [state.player1, state.player2]:
            # Reset aura bonuses
            for m in player.board:
                m.attack -= m.aura_attack_bonus
                m.aura_attack_bonus = 0

            # Apply aura effects
            for m in player.board:
                if "AURA" in m.mechanics:
                    text = self.card_db.get(m.card_id, {}).get("text", "")
                    match = re.search(r'다른.*아군.*하수인.*\+(\d+)\s*공격력', text)
                    if match:
                        bonus = int(match.group(1))
                        for other in player.board:
                            if other is not m:
                                other.attack += bonus
                                other.aura_attack_bonus += bonus

    # The Coin card data
    COIN_CARD_ID = "GAME_005"
    COIN_DATA = {
        "card_id": "GAME_005", "name": "The Coin", "card_type": "SPELL",
        "mana_cost": 0, "mechanics": [], "text": "",
    }

    def start_game(self, state: GameState):
        """Initialize game: shuffle, draw starting hands, give Coin to player 2."""
        # START_OF_GAME: check both players' decks for start-of-game effects
        for player in [state.player1, state.player2]:
            for card_id in player.deck:
                card_data = self.card_db.get(card_id, {})
                if "START_OF_GAME" in card_data.get("mechanics", []):
                    # Generic bonus: reduce hero power cost by 1
                    player.hero.hero_power_cost = max(0, player.hero.hero_power_cost - 1)
                    break  # Only apply once per player

        random.shuffle(state.player1.deck)
        random.shuffle(state.player2.deck)
        # Player 1 (goes first): draw 3 cards
        for _ in range(STARTING_HAND_FIRST):
            state.player1.draw_card()
        # Player 2 (goes second): draw 4 cards + The Coin
        for _ in range(STARTING_HAND_SECOND):
            state.player2.draw_card()
        state.player2.hand.append(self.COIN_CARD_ID)
        # Register coin in card_db so it can be played
        self.card_db[self.COIN_CARD_ID] = self.COIN_DATA

    def start_turn(self, state: GameState):
        """Start of turn phase (Hearthstone turn flow step 1-2)."""
        player = state.current_player

        # Phase 1: Gain mana crystal, unlock overload, reset hero
        player.max_mana = min(player.max_mana + 1, MAX_MANA)
        player.mana = player.max_mana - player.overload
        player.overload = 0
        player.hero.hero_power_used = False
        player.hero.attack = 0
        player.hero.attacks_this_turn = 0
        player.cards_played_this_turn = 0
        player.drawn_this_turn.clear()

        # Reset turn-based tracking
        player.spells_cast_last_turn = list(player.spells_cast_this_turn)
        player.spells_cast_this_turn.clear()
        player.hero_hp_at_turn_start = player.hero.health + player.hero.armor

        # Phase 2: Draw card
        player.draw_card()

        # Phase 3: Start-of-turn triggers ("At the start of your turn" effects)
        self._fire_start_of_turn(state)

    def _fire_start_of_turn(self, state: GameState):
        """Fire 'At the start of your turn' effects for all friendly minions."""
        player = state.current_player
        opponent = state.opponent

        # TITAN: use one ability per turn
        from src.simulator.card_handlers import TITAN_HANDLERS
        for m in list(player.board):
            if m.titan_turns_remaining > 0:
                m.titan_turns_remaining -= 1
                titan_fn = TITAN_HANDLERS.get(m.card_id)
                if titan_fn:
                    for i, used in enumerate(m.titan_abilities_used):
                        if not used:
                            m.titan_abilities_used[i] = True
                            titan_fn(self, state, player, m, i)
                            break
                else:
                    # Fallback for unknown titans: +2/+2
                    m.attack += 2
                    m.health += 2
                    m.max_health += 2

        for m in list(player.board):
            if m.is_dead:
                continue
            text = self.card_db.get(m.card_id, {}).get("text", "") or ""
            # "At the start of your turn" patterns (Korean)
            # "내 턴이 시작될 때" or "턴 시작 시"
            if "턴이 시작될 때" in text or "턴 시작 시" in text:
                from src.simulator.spell_parser import parse_spell_effects
                # Extract the effect portion after the trigger condition
                import re
                effect_match = re.search(r'(?:턴이 시작될 때|턴 시작 시)[,:]?\s*(.*)', text)
                if effect_match:
                    effects = parse_spell_effects(effect_match.group(1))
                    self._apply_battlecry_effects(state, player, m, effects)

    def end_turn(self, state: GameState):
        """End of turn phase (Hearthstone turn flow step 4-5)."""
        player = state.current_player

        # Phase 1: End-of-turn triggers ("At the end of your turn" effects)
        self._fire_end_of_turn(state)

        # Phase 2: Cleanup
        for m in player.board:
            # FREEZE: only thaw if the minion didn't attack this turn
            if m.frozen:
                if m.attacks_this_turn == 0:
                    m.frozen = False
            m.attacks_this_turn = 0
            m.summoned_this_turn = False
        player.hero.attack = 0
        player.hero.attacks_this_turn = 0

        # Remove echo copies from hand at end of turn
        if player.echo_cards:
            player.hand = [c for c in player.hand if c not in player.echo_cards]
            player.echo_cards.clear()

        # Remove dead minions from end-of-turn effects
        self.remove_dead_minions(state)

        # Switch turn
        state.switch_turn()
        self.apply_auras(state)

    def _fire_board_triggers(self, state: GameState, trigger_type: str, **ctx):
        """Fire ongoing trigger effects for board minions matching trigger_type."""
        player = state.current_player

        TRIGGER_PATTERNS = {
            "on_spell_cast": [r"주문을 시전[할한] (?:때마다|후에)"],
            "on_attack": [r"이 하수인이 공격[할한] (?:때마다|후에)", r"공격한 후에"],
            "on_hero_power": [r"영웅 능력을 사용[할한] (?:때마다|후에)"],
            "on_minion_death": [r"하수인이 (?:죽은|사망[할한]) (?:때마다|후에)"],
            "on_play_minion": [r"하수인을 (?:낼|낸) (?:때마다|후에)"],
            "on_draw": [r"카드를 (?:뽑을|뽑은) (?:때마다|후에)"],
        }

        patterns = TRIGGER_PATTERNS.get(trigger_type, [])
        if not patterns:
            return

        for m in list(player.board):
            if m.is_dead:
                continue
            # Skip INSPIRE minions for on_hero_power — already handled by use_hero_power()
            if trigger_type == "on_hero_power" and "INSPIRE" in m.mechanics:
                continue
            text = self.card_db.get(m.card_id, {}).get("text", "") or ""
            clean = re.sub(r'<[^>]+>', '', text).replace('[x]', '').replace('\n', ' ')

            for pattern in patterns:
                match = re.search(pattern, clean)
                if match:
                    # Extract the effect after the trigger pattern
                    effect_start = match.end()
                    effect_text = clean[effect_start:].strip().rstrip('.')
                    if effect_text:
                        from src.simulator.spell_parser import parse_spell_effects
                        effects = parse_spell_effects(effect_text)
                        if effects:
                            self._apply_battlecry_effects(state, player, m, effects)
                    break

    def _fire_end_of_turn(self, state: GameState):
        """Fire 'At the end of your turn' effects for all friendly minions."""
        player = state.current_player
        for m in list(player.board):
            if m.is_dead:
                continue
            text = self.card_db.get(m.card_id, {}).get("text", "") or ""
            # "At the end of your turn" patterns (Korean)
            # "내 턴이 끝날 때" or "턴 종료 시"
            if "턴이 끝날 때" in text or "턴 종료 시" in text:
                from src.simulator.spell_parser import parse_spell_effects
                import re
                effect_match = re.search(r'(?:턴이 끝날 때|턴 종료 시)[,:]?\s*(.*)', text)
                if effect_match:
                    effects = parse_spell_effects(effect_match.group(1))
                    self._apply_battlecry_effects(state, player, m, effects)

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

        # FREEZE: only freeze if actual damage was dealt (divine shield blocks it)
        if "FREEZE" in attacker.mechanics and damage_to_defender > 0:
            defender.frozen = True
        if "FREEZE" in defender.mechanics and damage_to_attacker > 0:
            attacker.frozen = True

        # FRENZY: trigger once on first damage
        if state is not None:
            self._check_frenzy(attacker, state)
            self._check_frenzy(defender, state)

        # ENRAGE
        if state is not None:
            self.apply_enrage(state)

        # HONORABLE_KILL: if attacker killed defender exactly (defender died, attacker alive)
        if state is not None and defender.is_dead and not attacker.is_dead:
            if "HONORABLE_KILL" in attacker.mechanics:
                from src.simulator.spell_parser import parse_honorable_kill_effects
                hk_effects = parse_honorable_kill_effects(
                    self.card_db.get(attacker.card_id, {}).get("text", ""))
                for player in [state.player1, state.player2]:
                    if attacker in player.board:
                        self._apply_battlecry_effects(state, player, attacker, hk_effects)
                        break

        # OVERKILL: if defender died with excess damage (health < 0)
        if state is not None and defender.is_dead and defender.health < 0:
            if "OVERKILL" in attacker.mechanics:
                from src.simulator.spell_parser import parse_overkill_effects
                ok_effects = parse_overkill_effects(
                    self.card_db.get(attacker.card_id, {}).get("text", ""))
                for player in [state.player1, state.player2]:
                    if attacker in player.board:
                        self._apply_battlecry_effects(state, player, attacker, ok_effects)
                        break

        # Fire ongoing board triggers for attack
        if state is not None:
            self._fire_board_triggers(state, "on_attack")

    def attack_hero(self, attacker: MinionState, hero: HeroState,
                    state: GameState | None = None):
        # Check secrets before attack resolves
        if state is not None:
            self.check_secrets(state, "attack_hero", attacker=attacker)
            if attacker.is_dead:
                return  # Secret killed the attacker
        damage_dealt = hero.take_damage(attacker.attack)
        attacker.attacks_this_turn += 1
        if attacker.stealth:
            attacker.stealth = False

        # LIFESTEAL
        if attacker.lifesteal and damage_dealt > 0 and state is not None:
            owner_hero = state.current_player.hero
            owner_hero.health = min(owner_hero.health + damage_dealt, owner_hero.max_health)

        # Fire ongoing board triggers for attack
        if state is not None:
            self._fire_board_triggers(state, "on_attack")

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
                    # Check for special deathrattle weapon equip
                    card_entry = self.card_db.get(m.card_id, {})
                    dr_weapon = card_entry.get("_deathrattle_weapon")
                    if dr_weapon:
                        player.hero.weapon = WeaponState(
                            card_id=dr_weapon["card_id"], name=dr_weapon["name"],
                            attack=dr_weapon["attack"], durability=dr_weapon["durability"],
                        )
                    effects = parse_deathrattle_effects(card_entry.get("text", ""))
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

        # STARSHIP_PIECE: track dead pieces and summon Starship when enough collected
        for player in (state.player1, state.player2):
            for m in player.board:
                if m.is_dead and "STARSHIP_PIECE" in m.mechanics:
                    player.starship_parts += 1
            if player.starship_parts >= 3 and not player.board_full:
                player.board.append(MinionState(
                    card_id="starship", name="Starship",
                    attack=8, health=8, max_health=8,
                    mana_cost=0, rush=True, mechanics=["RUSH"],
                    summoned_this_turn=True,
                ))
                player.starship_parts = 0

        any_died = False
        for player in (state.player1, state.player2):
            dead_count = sum(1 for m in player.board if m.is_dead)
            if dead_count > 0:
                any_died = True
            player.friendly_deaths_this_game += dead_count
            player.corpses += dead_count  # DK corpse resource
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
        self.apply_auras(state)

        # Fire ongoing board triggers for minion death
        if any_died:
            self._fire_board_triggers(state, "on_minion_death")

    def play_minion(self, state: GameState, card_data: dict,
                    hand_position: int | None = None) -> MinionState | None:
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

        # CORRUPT: if this card was corrupted, apply +2/+2 bonus as generic upgrade
        card_id = card_data.get("card_id", "")
        if card_id in player.corrupted_cards:
            minion.attack += 2
            minion.health += 2
            minion.max_health += 2
            del player.corrupted_cards[card_id]

        # Record played card
        player.played_cards_this_game.append({
            "card_id": card_data.get("card_id", ""),
            "card_type": "MINION",
            "mana_cost": card_data.get("mana_cost", 0),
            "turn": state.turn,
            "mechanics": card_data.get("mechanics", []),
            "race": card_data.get("race", ""),
        })

        # Check card-specific handler
        from src.simulator.card_handlers import CARD_HANDLERS
        handler = CARD_HANDLERS.get(card_data.get("card_id", ""))
        if handler:
            handler(self, state, player, minion)
            # Skip normal battlecry parsing for handled cards
        elif "BATTLECRY" in mechanics:
            # Apply battlecry
            from src.simulator.spell_parser import parse_battlecry_effects
            effects = parse_battlecry_effects(card_data.get("text", ""))
            self._apply_battlecry_effects(state, player, minion, effects)

        # Battlecry multiplier (e.g. Shudderblock)
        if player.next_battlecry_multiplier > 1 and "BATTLECRY" in mechanics:
            from src.simulator.spell_parser import parse_battlecry_effects as _parse_bc
            bc_effects = _parse_bc(card_data.get("text", ""))
            for _ in range(player.next_battlecry_multiplier - 1):
                handler = CARD_HANDLERS.get(card_data.get("card_id", ""))
                if handler:
                    handler(self, state, player, minion)
                elif bc_effects:
                    self._apply_battlecry_effects(state, player, minion, bc_effects)
            player.next_battlecry_multiplier = 1

        # COMBO: apply combo bonus if another card was played this turn
        if "COMBO" in mechanics and player.cards_played_this_turn > 0:
            from src.simulator.spell_parser import parse_combo_effects
            combo_effects = parse_combo_effects(card_data.get("text", ""))
            self._apply_battlecry_effects(state, player, minion, combo_effects)

        # Increment cards played counter (after combo check so combo sees previous count)
        player.cards_played_this_turn += 1

        # QUEST progress: increment on every card played
        self._check_quest_progress(player)

        # ECHO: add a temporary copy to hand
        if "ECHO" in mechanics:
            card_id = card_data.get("card_id", "")
            if card_id and len(player.hand) < 10:  # HAND_LIMIT
                player.hand.append(card_id)
                player.echo_cards.append(card_id)

        # OUTCAST: apply bonus if played from leftmost or rightmost hand position
        if "OUTCAST" in mechanics and hand_position is not None:
            # Card has already been removed from hand, so len(hand) is one less
            was_outcast = (hand_position == 0 or hand_position == len(player.hand))
            if was_outcast:
                from src.simulator.spell_parser import parse_outcast_effects
                outcast_effects = parse_outcast_effects(card_data.get("text", ""))
                self._apply_battlecry_effects(state, player, minion, outcast_effects)

        # MINIATURIZE: summon a 1/1 copy
        if "MINIATURIZE" in mechanics and not player.board_full:
            mini = MinionState(
                card_id=card_data.get("card_id", "") + "_mini",
                name=card_data.get("name", "") + " (Mini)",
                attack=1, health=1, max_health=1,
                mana_cost=1,
                taunt=minion.taunt,
                mechanics=list(mechanics),
                summoned_this_turn=True,
            )
            player.board.append(mini)

        # SPELLBURST: activate on play so it triggers on next spell
        if "SPELLBURST" in mechanics:
            minion.spellburst_active = True

        # DREDGE: look at bottom 3 cards of deck, put best on top
        if "DREDGE" in mechanics:
            self._do_dredge(player)

        # DISCOVER: pick from 3 random cards, add best to hand
        if "DISCOVER" in mechanics:
            self._discover(state, player)

        # MANATHIRST: bonus if max_mana >= threshold
        from src.simulator.spell_parser import parse_manathirst_effects
        threshold, mana_effects = parse_manathirst_effects(card_data.get("text", ""))
        if threshold > 0 and player.max_mana >= threshold:
            self._apply_battlecry_effects(state, player, minion, mana_effects)

        # INFUSE: check if friendly deaths meet threshold for bonus
        from src.simulator.spell_parser import parse_infuse_threshold, parse_infuse_effects
        infuse_threshold = parse_infuse_threshold(card_data.get("text", ""))
        if infuse_threshold > 0 and player.friendly_deaths_this_game >= infuse_threshold:
            infuse_effects = parse_infuse_effects(card_data.get("text", ""))
            self._apply_battlecry_effects(state, player, minion, infuse_effects)

        # MAGNETIC: merge with a friendly mech on board
        if "MAGNETIC" in mechanics:
            # Find a mech on the board (not the one we just placed)
            mech_target = None
            for m in player.board:
                if m is not minion and "MECHANICAL" in m.mechanics:
                    mech_target = m
                    break
            if mech_target:
                # Merge: add stats to existing mech, remove the new minion
                mech_target.attack += minion.attack
                mech_target.health += minion.health
                mech_target.max_health += minion.max_health
                if minion.taunt:
                    mech_target.taunt = True
                if minion.divine_shield:
                    mech_target.divine_shield = True
                if minion.windfury:
                    mech_target.windfury = True
                if minion.lifesteal:
                    mech_target.lifesteal = True
                if minion.poisonous:
                    mech_target.poisonous = True
                player.board.remove(minion)

        # CHOOSE_ONE: parse and apply first option as battlecry
        if "CHOOSE_ONE" in mechanics:
            from src.simulator.spell_parser import parse_choose_one_effects
            choose_effects = parse_choose_one_effects(card_data.get("text", ""))
            self._apply_battlecry_effects(state, player, minion, choose_effects)

        # COLOSSAL: summon additional appendage tokens
        if "COLOSSAL" in mechanics:
            text = card_data.get("text", "") or ""
            colossal_match = re.search(r'거대\s*\+(\d+)', text)
            appendage_count = int(colossal_match.group(1)) if colossal_match else 1
            for _ in range(appendage_count):
                if not player.board_full:
                    player.board.append(MinionState(
                        card_id=card_data.get("card_id", "") + "_appendage",
                        name=card_data.get("name", "") + " Appendage",
                        attack=1, health=1, max_health=1,
                        mana_cost=0, summoned_this_turn=True,
                    ))

        # EXCAVATE: simplified - draw a card as reward
        if "EXCAVATE" in mechanics:
            player.draw_card()

        # QUICKDRAW: bonus if card was drawn this turn
        card_id = card_data.get("card_id", "")
        if "QUICKDRAW" in mechanics and card_id in player.drawn_this_turn:
            from src.simulator.spell_parser import parse_quickdraw_effects
            qd_effects = parse_quickdraw_effects(card_data.get("text", ""))
            self._apply_battlecry_effects(state, player, minion, qd_effects)

        # JADE_GOLEM: summon jade golem if card text mentions it
        text = card_data.get("text", "") or ""
        if "비취 골렘" in text:
            self._summon_jade_golem(state, player)

        # HERALD: summon a Soldier token with class-specific effects, scaled by herald count
        if "HERALD" in mechanics and not player.board_full:
            player.herald_count += 1
            power = 1
            if player.herald_count >= 4:
                power = 4
            elif player.herald_count >= 2:
                power = 2
            soldier_atk = 1 * power
            soldier_hp = 1 * power
            hero_class = player.hero.hero_class
            soldier_mechs: list[str] = []
            if hero_class in ("DEATH_KNIGHT", "WARRIOR"):
                soldier_mechs = ["DEATHRATTLE"]
            soldier = MinionState(
                card_id="herald_soldier", name=f"Soldier ({power}x)",
                attack=soldier_atk, health=soldier_hp, max_health=soldier_hp,
                mana_cost=0, mechanics=soldier_mechs, summoned_this_turn=True,
            )
            # Register soldier deathrattle text for DEATH_KNIGHT/WARRIOR
            if hero_class in ("DEATH_KNIGHT", "WARRIOR"):
                self.card_db["herald_soldier"] = {
                    "card_id": "herald_soldier", "name": f"Soldier ({power}x)",
                    "text": f"죽음의 메아리: 적에게 피해를 {2 * power} 줍니다.",
                    "mechanics": ["DEATHRATTLE"],
                }
            # Class-specific bonus
            if hero_class == "DEMON_HUNTER":
                player.hero.attack += power
            elif hero_class == "ROGUE":
                player.draw_card()
            elif hero_class == "SHAMAN":
                for m in player.board:
                    m.attack += power
                    m.aura_attack_bonus += power
            player.board.append(soldier)

        # SHATTER: double stats for minions
        if "SHATTER" in mechanics:
            minion.attack *= 2
            minion.health *= 2
            minion.max_health *= 2

        # TITAN: set 3-turn ability counter
        if "TITAN" in mechanics:
            minion.titan_turns_remaining = 3

        # STARSHIP_PIECE: mark for parts tracking (deathrattle handled in remove_dead_minions)
        if "STARSHIP_PIECE" in mechanics and "DEATHRATTLE" not in minion.mechanics:
            minion.mechanics.append("DEATHRATTLE")

        # CORRUPT: mark hand cards with lower cost as corrupted
        card_cost = card_data.get("mana_cost", 0)
        self._check_corrupt_hand(player, card_cost)

        # Check opponent secrets on minion play
        self.check_secrets(state, "play_minion", minion=minion)

        # Fire ongoing board triggers for playing a minion
        self._fire_board_triggers(state, "on_play_minion")

        self.apply_auras(state)
        return minion

    def _apply_battlecry_effects(self, state: GameState, player: PlayerState,
                                  minion: MinionState, effects: list):
        """Apply a list of SpellEffect objects as battlecry/combo effects."""
        for eff in effects:
            if eff.effect_type == "damage":
                if eff.target in ("enemy_hero", "auto"):
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
            elif eff.effect_type == "buff" and eff.target == "double_stats":
                minion.attack *= 2
                minion.health *= 2
                minion.max_health *= 2
            elif eff.effect_type == "buff":
                minion.attack += eff.value
                minion.health += eff.value2
                minion.max_health += eff.value2
            elif eff.effect_type == "heal":
                # OVERHEAL: if already at max health, trigger overheal bonus
                if player.hero.health >= player.hero.max_health:
                    if "OVERHEAL" in (minion.mechanics if minion else []):
                        from src.simulator.spell_parser import parse_overheal_effects
                        oh_effects = parse_overheal_effects(
                            self.card_db.get(minion.card_id, {}).get("text", ""))
                        # Apply overheal effects (avoid infinite recursion by not re-checking overheal)
                        for oh_eff in oh_effects:
                            if oh_eff.effect_type == "armor":
                                player.hero.armor += oh_eff.value
                            elif oh_eff.effect_type == "draw":
                                for _ in range(oh_eff.value):
                                    player.draw_card()
                            elif oh_eff.effect_type == "buff":
                                minion.attack += oh_eff.value
                                minion.health += oh_eff.value2
                                minion.max_health += oh_eff.value2
                player.hero.health = min(player.hero.health + eff.value, player.hero.max_health)
            elif eff.effect_type == "armor":
                player.hero.armor += eff.value

            elif eff.effect_type == "grant_keyword":
                keyword = eff.target  # e.g., "RUSH", "TAUNT"
                if keyword == "RUSH":
                    minion.rush = True
                elif keyword == "TAUNT":
                    minion.taunt = True
                elif keyword == "WINDFURY":
                    minion.windfury = True
                elif keyword == "DIVINE_SHIELD":
                    minion.divine_shield = True
                elif keyword == "STEALTH":
                    minion.stealth = True
                elif keyword == "LIFESTEAL":
                    minion.lifesteal = True
                elif keyword == "POISONOUS":
                    minion.poisonous = True
                elif keyword == "REBORN":
                    minion.reborn = True
                if keyword not in minion.mechanics:
                    minion.mechanics.append(keyword)

            elif eff.effect_type == "cost_reduction":
                for card_id in player.hand:
                    cd = self.card_db.get(card_id, {})
                    if cd:
                        cd["mana_cost"] = max(0, cd.get("mana_cost", 0) - eff.value)

            elif eff.effect_type == "set_cost":
                for card_id in player.hand:
                    cd = self.card_db.get(card_id, {})
                    if cd:
                        cd["mana_cost"] = eff.value

            elif eff.effect_type == "random_summon":
                if not player.board_full:
                    candidates = [c for c in self.card_db.values()
                                  if c.get("card_type") == "MINION"
                                  and not c.get("card_id", "").startswith("herald_")
                                  and not c.get("card_id", "").endswith("_mini")]
                    if eff.value > 0:
                        candidates = [c for c in candidates if c.get("mana_cost") == eff.value]
                    if candidates:
                        pick = random.choice(candidates)
                        player.board.append(MinionState(
                            card_id=pick["card_id"], name=pick.get("name", ""),
                            attack=pick.get("attack", 1), health=pick.get("health", 1),
                            max_health=pick.get("health", 1), mana_cost=pick.get("mana_cost", 0),
                            summoned_this_turn=True,
                        ))

            elif eff.effect_type == "random_generate":
                if len(player.hand) < 10:
                    candidates = [c for c in self.card_db.values()
                                  if c.get("card_type") in ("MINION", "SPELL")
                                  and c.get("card_id", "").upper() != "GAME_005"]
                    if candidates:
                        pick = random.choice(candidates)
                        player.hand.append(pick["card_id"])

            elif eff.effect_type == "discover":
                self._discover(state, player)

            elif eff.effect_type == "transform":
                # Transform highest health enemy minion into random same-cost minion
                if state.opponent.board:
                    target = max(state.opponent.board, key=lambda m: m.health)
                    cost = target.mana_cost
                    candidates = [c for c in self.card_db.values()
                                  if c.get("card_type") == "MINION" and c.get("mana_cost") == cost
                                  and not c.get("card_id", "").endswith("_mini")]
                    if candidates:
                        pick = random.choice(candidates)
                        idx = state.opponent.board.index(target)
                        state.opponent.board[idx] = MinionState(
                            card_id=pick["card_id"], name=pick.get("name", ""),
                            attack=pick.get("attack", 1), health=pick.get("health", 1),
                            max_health=pick.get("health", 1), mana_cost=pick.get("mana_cost", 0),
                            summoned_this_turn=True,
                        )
                    else:
                        target.health = 0

            elif eff.effect_type == "resurrect":
                for _ in range(eff.value):
                    if not player.board_full:
                        candidates = [c for c in self.card_db.values()
                                      if c.get("card_type") == "MINION"
                                      and c.get("mana_cost", 99) <= 5
                                      and not c.get("card_id", "").endswith("_mini")]
                        if candidates:
                            pick = random.choice(candidates)
                            player.board.append(MinionState(
                                card_id=pick["card_id"], name=pick.get("name", ""),
                                attack=pick.get("attack", 1), health=pick.get("health", 1),
                                max_health=pick.get("health", 1), mana_cost=pick.get("mana_cost", 0),
                                summoned_this_turn=True,
                            ))

            elif eff.effect_type == "shuffle_into_deck":
                # Shuffle random cards from card_db into player's deck
                candidates = [c for c in self.card_db.values()
                              if c.get("card_type") in ("MINION", "SPELL")
                              and c.get("card_id", "").upper() != "GAME_005"]
                for _ in range(eff.value):
                    if candidates:
                        pick = random.choice(candidates)
                        player.deck.append(pick["card_id"])
                random.shuffle(player.deck)

    def _apply_single_spell_effect(self, state: GameState, player: PlayerState,
                                    opponent: PlayerState, eff, spell_power: int, target=None):
        """Apply a single parsed spell effect."""
        if eff.effect_type == "damage":
            damage = eff.value + spell_power
            if eff.target == "enemy_hero":
                opponent.hero.take_damage(damage)
            elif eff.target == "enemy_minion" and opponent.board:
                if target and isinstance(target, MinionState) and self._can_be_targeted(target):
                    target.take_damage(damage)
                else:
                    targetable = [m for m in opponent.board if self._can_be_targeted(m)]
                    if targetable:
                        max(targetable, key=lambda m: m.health).take_damage(damage)
            elif eff.target == "auto":
                opponent.hero.take_damage(damage)

        elif eff.effect_type == "aoe_damage":
            damage = eff.value + spell_power
            if eff.target == "all_minions":
                for m in player.board + opponent.board:
                    m.take_damage(damage)
            elif eff.target == "all_enemy_minions":
                for m in opponent.board:
                    m.take_damage(damage)

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

        elif eff.effect_type == "silence":
            if target and isinstance(target, MinionState):
                if self._can_be_targeted(target):
                    self.silence_minion(target)
            elif opponent.board:
                targetable = [m for m in opponent.board if self._can_be_targeted(m)]
                if targetable:
                    t = max(targetable, key=lambda m: m.health)
                    self.silence_minion(t)

        elif eff.effect_type == "summon" and not player.board_full:
            player.board.append(MinionState(
                card_id="token", name="Token",
                attack=eff.value, health=eff.value2, max_health=eff.value2,
                mana_cost=0,
            ))

    def play_spell(self, state: GameState, card_data: dict, target=None):
        player = state.current_player
        opponent = state.opponent
        player.mana -= card_data.get("mana_cost", 0)
        # OVERLOAD
        overload = card_data.get("overload", 0)
        if overload:
            player.overload += overload

        mechanics = card_data.get("mechanics", [])

        # SECRET: add to secrets list, don't resolve effects
        if "SECRET" in mechanics:
            player.secrets.append(card_data.get("card_id", ""))
            player.cards_played_this_turn += 1
            return

        # QUEST: set up quest tracking
        if "QUEST" in mechanics:
            from src.simulator.spell_parser import parse_quest_threshold
            player.active_quest = card_data.get("card_id", "")
            player.quest_threshold = parse_quest_threshold(card_data.get("text", ""))
            player.quest_progress = 0
            player.quest_reward_given = False
            player.cards_played_this_turn += 1
            return

        # The Coin: gain 1 mana crystal this turn only
        if card_data.get("card_id") == self.COIN_CARD_ID:
            player.mana = min(player.mana + 1, MAX_MANA)
            player.cards_played_this_turn += 1
            return

        # Record spell played
        player.spells_cast_this_turn.append(card_data.get("card_id", ""))
        player.played_cards_this_game.append({
            "card_id": card_data.get("card_id", ""),
            "card_type": "SPELL",
            "mana_cost": card_data.get("mana_cost", 0),
            "turn": state.turn,
            "mechanics": card_data.get("mechanics", []),
        })

        from src.simulator.spell_parser import parse_spell_effects
        effects = parse_spell_effects(card_data.get("text", ""))

        # Calculate spell power bonus from friendly minions
        spell_power = self._get_spell_power(state)

        # SHATTER bonus: double spell damage
        if "SHATTER" in mechanics:
            spell_power = spell_power * 2 + 2

        for eff in effects:
            self._apply_single_spell_effect(state, player, opponent, eff, spell_power, target)

        # Tyrande double-cast: replay spell effects
        if player.next_spell_cast_twice_count > 0:
            player.next_spell_cast_twice_count -= 1
            for eff in effects:
                self._apply_single_spell_effect(state, player, opponent, eff, spell_power, target)

        # MANATHIRST: bonus if max_mana >= threshold
        from src.simulator.spell_parser import parse_manathirst_effects
        threshold, mana_effects = parse_manathirst_effects(card_data.get("text", ""))
        if threshold > 0 and player.max_mana >= threshold:
            # Apply manathirst effects like normal spell effects
            for eff in mana_effects:
                if eff.effect_type == "damage":
                    damage = eff.value + self._get_spell_power(state)
                    opponent.hero.take_damage(damage)
                elif eff.effect_type == "draw":
                    for _ in range(eff.value):
                        player.draw_card()

        player.cards_played_this_turn += 1

        # Check secrets triggered by spell cast
        self.check_secrets(state, "play_spell")

        # QUEST progress: increment on every card played
        self._check_quest_progress(player)

        # TWINSPELL: add a copy without TWINSPELL to hand
        if "TWINSPELL" in mechanics:
            card_id = card_data.get("card_id", "")
            if card_id and len(player.hand) < 10:
                # Add the card back to hand; the copy conceptually lacks TWINSPELL
                # but since we key off card_db, we mark it by adding a suffix
                twin_id = card_id + "_twin"
                # Register twin copy in card_db without TWINSPELL
                twin_data = dict(card_data)
                twin_mechanics = [m for m in mechanics if m != "TWINSPELL"]
                twin_data["mechanics"] = twin_mechanics
                twin_data["card_id"] = twin_id
                self.card_db[twin_id] = twin_data
                player.hand.append(twin_id)

        # DREDGE: look at bottom 3 cards of deck, put best on top
        if "DREDGE" in mechanics:
            self._do_dredge(player)

        # DISCOVER: pick from 3 random cards, add best to hand
        if "DISCOVER" in mechanics:
            self._discover(state, player)

        # CHOOSE_ONE: parse and apply first option
        if "CHOOSE_ONE" in mechanics:
            from src.simulator.spell_parser import parse_choose_one_effects
            choose_effects = parse_choose_one_effects(card_data.get("text", ""))
            # Apply like spell effects
            for eff in choose_effects:
                if eff.effect_type == "damage":
                    damage = eff.value + self._get_spell_power(state)
                    if eff.target == "enemy_hero":
                        opponent.hero.take_damage(damage)
                    elif eff.target in ("enemy_minion", "auto") and opponent.board:
                        t = max(opponent.board, key=lambda m: m.health)
                        t.take_damage(damage)
                    else:
                        opponent.hero.take_damage(damage)
                elif eff.effect_type == "draw":
                    for _ in range(eff.value):
                        player.draw_card()
                elif eff.effect_type == "buff" and player.board:
                    t = player.board[-1]
                    t.attack += eff.value
                    t.health += eff.value2
                    t.max_health += eff.value2
                elif eff.effect_type == "armor":
                    player.hero.armor += eff.value
                elif eff.effect_type == "heal":
                    player.hero.health = min(player.hero.health + eff.value, player.hero.max_health)

        # EXCAVATE: simplified - draw a card as reward
        if "EXCAVATE" in mechanics:
            player.draw_card()

        # QUICKDRAW: bonus if card was drawn this turn
        card_id = card_data.get("card_id", "")
        if "QUICKDRAW" in mechanics and card_id in player.drawn_this_turn:
            from src.simulator.spell_parser import parse_quickdraw_effects
            qd_effects = parse_quickdraw_effects(card_data.get("text", ""))
            for eff in qd_effects:
                if eff.effect_type == "damage":
                    damage = eff.value + self._get_spell_power(state)
                    opponent.hero.take_damage(damage)
                elif eff.effect_type == "draw":
                    for _ in range(eff.value):
                        player.draw_card()

        # JADE_GOLEM: summon jade golem if card text mentions it
        text = card_data.get("text", "") or ""
        if "비취 골렘" in text:
            self._summon_jade_golem(state, player)

        # CORRUPT: mark hand cards with lower cost as corrupted
        card_cost = card_data.get("mana_cost", 0)
        self._check_corrupt_hand(player, card_cost)

        # Fire ongoing board triggers for spell cast
        self._fire_board_triggers(state, "on_spell_cast")

        # Trigger spellburst on friendly minions
        self._check_spellburst(state)
        self.remove_dead_minions(state)

    def _get_spell_power(self, state: GameState) -> int:
        """Calculate total spell damage bonus from friendly minions with SPELLPOWER.
        Checks card text for 'spell power +N' pattern, defaults to +1."""
        total = 0
        for m in state.current_player.board:
            if "SPELLPOWER" in m.mechanics:
                text = self.card_db.get(m.card_id, {}).get("text", "") or ""
                import re
                sp_match = re.search(r'주문\s*공격력\s*\+(\d+)', text)
                if sp_match:
                    total += int(sp_match.group(1))
                else:
                    total += 1
        return total

    def _check_quest_progress(self, player: PlayerState):
        """Increment quest progress and check for completion."""
        if player.active_quest and not player.quest_reward_given:
            player.quest_progress += 1
            if player.quest_progress >= player.quest_threshold:
                player.quest_reward_given = True
                # Quest reward: draw 2 cards + hero power cost becomes 0
                player.draw_card()
                player.draw_card()
                player.hero.hero_power_cost = 0

    def _check_frenzy(self, minion: MinionState, state: GameState):
        """Trigger frenzy effect if the minion was damaged for the first time."""
        if "FRENZY" not in minion.mechanics:
            return
        if minion.frenzy_triggered or minion.is_dead:
            return
        if minion.health < minion.max_health:
            minion.frenzy_triggered = True
            from src.simulator.spell_parser import parse_frenzy_effects
            effects = parse_frenzy_effects(self.card_db.get(minion.card_id, {}).get("text", ""))
            # Find which player owns this minion
            for player in [state.player1, state.player2]:
                if minion in player.board:
                    self._apply_battlecry_effects(state, player, minion, effects)
                    break

    def _check_spellburst(self, state: GameState):
        """Trigger spellburst for all friendly minions with active spellburst."""
        player = state.current_player
        for m in player.board:
            if "SPELLBURST" in m.mechanics and m.spellburst_active and not m.is_dead:
                m.spellburst_active = False
                from src.simulator.spell_parser import parse_spellburst_effects
                effects = parse_spellburst_effects(self.card_db.get(m.card_id, {}).get("text", ""))
                self._apply_battlecry_effects(state, player, m, effects)

    def check_secrets(self, state: GameState, trigger: str, **ctx):
        """Check and trigger opponent secrets based on game events.

        Supported triggers:
        - 'attack_hero': when opponent's hero is attacked
        - 'play_minion': when a minion is played
        - 'play_spell': when a spell is cast (targeting hero)
        """
        opponent = state.opponent
        if not opponent.secrets:
            return

        triggered = None
        for secret_id in opponent.secrets:
            secret_data = self.card_db.get(secret_id, {})
            text = (secret_data.get("text", "") or "").lower()

            if trigger == "attack_hero":
                # Ice Block style: prevent lethal / redirect attack
                # Explosive Trap: deal damage to attacker
                if "공격" in text and "영웅" in text:
                    triggered = secret_id
                    # Simple: deal 2 damage to all enemy minions
                    attacker = ctx.get("attacker")
                    if attacker and isinstance(attacker, MinionState):
                        attacker.take_damage(2)
                    break
            elif trigger == "play_minion":
                # Mirror Entity / Snipe style
                if "하수인" in text and ("소환" in text or "내면" in text):
                    triggered = secret_id
                    minion = ctx.get("minion")
                    if minion:
                        minion.take_damage(4)  # Snipe-style
                    break
            elif trigger == "play_spell":
                # Counterspell style
                if "주문" in text and ("무효" in text or "방해" in text):
                    triggered = secret_id
                    break

        if triggered:
            opponent.secrets.remove(triggered)

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
                if self._can_be_targeted(target):
                    target.take_damage(1)
                else:
                    opponent.hero.take_damage(1)
            else:
                opponent.hero.take_damage(1)
        elif hero_class == "WARRIOR":
            player.hero.armor += 2
        elif hero_class == "PRIEST":
            if target and isinstance(target, MinionState):
                if not self._can_be_targeted(target):
                    player.hero.health = min(player.hero.health + 2, player.hero.max_health)
                else:
                    target.health = min(target.health + 2, target.max_health)
            else:
                player.hero.health = min(player.hero.health + 2, player.hero.max_health)
        elif hero_class == "HUNTER":
            opponent.hero.take_damage(2)
        elif hero_class == "PALADIN":
            if not player.board_full:
                player.board.append(MinionState(card_id="CS2_101t", name="Silver Hand Recruit",
                    attack=1, health=1, max_health=1, mana_cost=0, summoned_this_turn=True))
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
                totem = random.choice(totems)
                totem.summoned_this_turn = True
                player.board.append(totem)
        elif hero_class == "DRUID":
            player.hero.armor += 1
            player.hero.attack += 1
        elif hero_class == "DEMON_HUNTER":
            player.hero.attack += 1
        elif hero_class == "DEATH_KNIGHT":
            if not player.board_full:
                player.board.append(MinionState(card_id="dk_ghoul", name="Ghoul",
                    attack=1, health=1, max_health=1, mana_cost=0, summoned_this_turn=True))

        # INSPIRE: trigger on friendly minions after hero power use
        from src.simulator.spell_parser import parse_inspire_effects
        for m in list(player.board):
            if m.is_dead:
                continue
            if "INSPIRE" in m.mechanics:
                insp_effects = parse_inspire_effects(
                    self.card_db.get(m.card_id, {}).get("text", ""))
                self._apply_battlecry_effects(state, player, m, insp_effects)

        # Fire ongoing board triggers for hero power use
        self._fire_board_triggers(state, "on_hero_power")

    def _do_dredge(self, player: PlayerState):
        """DREDGE: look at bottom 3 cards of deck, put the best (highest mana cost) on top."""
        if not player.deck:
            return
        bottom_count = min(3, len(player.deck))
        # Bottom cards are at end of deck list (deck[0] is top)
        bottom_cards = player.deck[-bottom_count:]
        # Pick the one with highest mana cost
        best = max(bottom_cards, key=lambda cid: self.card_db.get(cid, {}).get("mana_cost", 0))
        player.deck.remove(best)
        player.deck.insert(0, best)

    def _discover(self, state: GameState, player: PlayerState, filter_fn=None):
        """DISCOVER: present 3 random cards from card_db, AI picks lowest cost one, add to hand.
        Class cards have 4x weighting per official Hearthstone rules."""
        candidates = list(self.card_db.values())
        if filter_fn:
            candidates = [c for c in candidates if filter_fn(c)]
        # Filter out tokens and coins
        candidates = [c for c in candidates if c.get("card_type") in ("MINION", "SPELL", "WEAPON")
                       and c.get("card_id", "").upper() != "GAME_005"
                       and not c.get("card_id", "").endswith("_mini")
                       and not c.get("card_id", "").endswith("_twin")]
        if not candidates:
            return
        # 4x weighting for player's class cards
        hero_class = player.hero.hero_class
        weighted = []
        for c in candidates:
            card_class = c.get("hero_class", "NEUTRAL")
            if card_class == hero_class:
                weighted.extend([c] * 4)  # 4x weight
            else:
                weighted.append(c)
        # Pick 3 unique cards
        choices = []
        seen_ids = set()
        random.shuffle(weighted)
        for c in weighted:
            cid = c.get("card_id", "")
            if cid not in seen_ids:
                choices.append(c)
                seen_ids.add(cid)
            if len(choices) >= 3:
                break
        if not choices:
            return
        # AI picks the lowest cost one (simple heuristic)
        pick = min(choices, key=lambda c: c.get("mana_cost", 99))
        card_id = pick.get("card_id", "")
        if card_id and len(player.hand) < 10:
            player.hand.append(card_id)

    def _check_corrupt_hand(self, player: PlayerState, played_cost: int):
        """CORRUPT: mark hand cards with CORRUPT mechanic and cost < played_cost as corrupted."""
        for card_id in player.hand:
            card_data = self.card_db.get(card_id, {})
            if "CORRUPT" in card_data.get("mechanics", []):
                if card_data.get("mana_cost", 0) < played_cost:
                    player.corrupted_cards[card_id] = True

    def _summon_jade_golem(self, state: GameState, player: PlayerState):
        """Summon a Jade Golem with stats equal to player's jade counter, then increment (max 30)."""
        player.jade_counter = min(player.jade_counter + 1, 30)
        stats = player.jade_counter
        if not player.board_full:
            player.board.append(MinionState(
                card_id="jade_golem", name="Jade Golem",
                attack=stats, health=stats, max_health=stats,
                mana_cost=0, summoned_this_turn=True,
            ))

    def get_legal_actions(self, state: GameState) -> list:
        from src.simulator.actions import PlayCard, Attack, HeroPower, EndTurn, TradeCard, ForgeCard
        actions = []
        player = state.current_player
        opponent = state.opponent

        for i, card_id in enumerate(player.hand):
            card_data = self.card_db.get(card_id)
            if not card_data:
                continue
            # TRADEABLE: can trade for 1 mana if player has a deck
            if "TRADEABLE" in card_data.get("mechanics", []) and player.mana >= 1 and player.deck:
                actions.append(TradeCard(card_id=card_id, hand_idx=i))
            # FORGE: spend 2 mana to upgrade card in hand
            if "FORGE" in card_data.get("mechanics", []) and player.mana >= 2:
                actions.append(ForgeCard(card_id=card_id, hand_idx=i))
            if card_data.get("mana_cost", 99) <= player.mana:
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
