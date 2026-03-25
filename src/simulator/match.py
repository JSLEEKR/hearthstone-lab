from __future__ import annotations
import random
import logging
from dataclasses import dataclass, field
from src.simulator.ai import BaseAI
from src.simulator.engine import GameEngine
from src.simulator.game_state import GameState, PlayerState, HeroState, WeaponState
from src.simulator.actions import PlayCard, Attack, HeroPower, EndTurn, TradeCard, ForgeCard
from src.simulator.event_log import GameEventLog

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    winner: str | None  # "A", "B", or None
    turns: int
    log: list[dict] = field(default_factory=list)  # event log dicts
    p1_hero: str = ""
    p2_hero: str = ""


def run_match(deck_a: list[str], deck_b: list[str], hero_a: str, hero_b: str,
              card_db: dict, max_turns: int = 45, ai_class=None) -> MatchResult:
    engine = GameEngine(card_db=card_db)
    if ai_class is None:
        from src.simulator.ai import RuleBasedAI
        ai = RuleBasedAI()
    elif isinstance(ai_class, type):
        ai = ai_class()
    else:
        ai = ai_class  # already an instance

    state = GameState(
        player1=PlayerState(hero=HeroState(hero_class=hero_a), deck=list(deck_a)),
        player2=PlayerState(hero=HeroState(hero_class=hero_b), deck=list(deck_b)),
    )

    log = GameEventLog()

    # Log game start
    log.append(0, -1, "GAME_START", "game", hero_a=hero_a, hero_b=hero_b)

    engine.start_game(state)

    # Mulligan
    keep_1 = ai.mulligan(state.player1.hand, card_db)
    returned_1 = [c for c in state.player1.hand if c not in keep_1]
    _do_mulligan(state.player1, keep_1)
    log.append(0, 0, "MULLIGAN", "game",
               kept=len(keep_1), returned=len(returned_1))

    keep_2 = ai.mulligan(state.player2.hand, card_db)
    returned_2 = [c for c in state.player2.hand if c not in keep_2]
    _do_mulligan(state.player2, keep_2)
    log.append(0, 1, "MULLIGAN", "game",
               kept=len(keep_2), returned=len(returned_2))

    turn_count = 0
    while not state.game_over and turn_count < max_turns:
        engine.start_turn(state)
        turn_count += 1

        p = state.current_player
        log.append(turn_count, state.current_player_idx, "TURN_START", "game",
                   mana=p.mana, hand_size=len(p.hand))

        # Log draw (start_turn draws a card)
        if p.drawn_this_turn:
            card_id = p.drawn_this_turn[-1]
            card_name = card_db.get(card_id, {}).get("name", card_id)
            log.append(turn_count, state.current_player_idx, "DRAW", card_id,
                       name=card_name)
        elif p.fatigue_counter > 0:
            log.append(turn_count, state.current_player_idx, "FATIGUE", "fatigue",
                       damage=p.fatigue_counter)

        action_count = 0
        while action_count < 50:
            action = ai.choose_action(state, engine)
            if isinstance(action, EndTurn):
                break
            _execute_action(engine, state, action, card_db, log, turn_count)
            engine.remove_dead_minions(state)
            # Log minion deaths
            # (dead minions already removed, we track via board changes)
            if state.game_over:
                break
            action_count += 1

        if state.game_over:
            break

        # Log turn end with board state summary
        cur = state.current_player
        opp = state.opponent
        log.append(turn_count, state.current_player_idx, "TURN_END", "game",
                   board_size=len(cur.board), opp_board_size=len(opp.board),
                   hero_hp=cur.hero.health, opp_hero_hp=opp.hero.health)

        engine.end_turn(state)

    winner = None
    if state.game_over:
        if state.winner_idx == 0:
            winner = "A"
        elif state.winner_idx == 1:
            winner = "B"

    log.append(turn_count, -1, "GAME_OVER", "game",
               winner=winner or "draw", final_turn=turn_count,
               p1_hp=state.player1.hero.health, p2_hp=state.player2.hero.health)

    return MatchResult(winner=winner, turns=turn_count,
                       log=log.to_dicts(), p1_hero=hero_a, p2_hero=hero_b)


def _do_mulligan(player: PlayerState, keep: list[str]):
    new_hand = []
    returned = []
    keep_copy = list(keep)
    for card_id in player.hand:
        if card_id in keep_copy:
            new_hand.append(card_id)
            keep_copy.remove(card_id)
        else:
            returned.append(card_id)
    player.hand = new_hand
    player.deck.extend(returned)
    random.shuffle(player.deck)
    for _ in range(len(returned)):
        player.draw_card()


def _execute_action(engine: GameEngine, state: GameState, action, card_db: dict,
                    log: GameEventLog, turn_count: int):
    if isinstance(action, PlayCard):
        player = state.current_player
        if action.hand_idx < len(player.hand):
            card_id = player.hand.pop(action.hand_idx)
            card_data = card_db.get(card_id, {})
            card_type = card_data.get("card_type", "MINION")
            card_name = card_data.get("name", card_id)
            cost = card_data.get("mana_cost", 0)

            if card_type == "MINION":
                engine.play_minion(state, card_data, hand_position=action.hand_idx)
                log.append(turn_count, state.current_player_idx, "PLAY_MINION", card_id,
                           name=card_name, cost=cost,
                           attack=card_data.get("attack", 0),
                           health=card_data.get("health", 0))
            elif card_type == "SPELL":
                engine.play_spell(state, card_data)
                log.append(turn_count, state.current_player_idx, "PLAY_SPELL", card_id,
                           name=card_name, cost=cost)
            elif card_type == "WEAPON":
                player.hero.weapon = WeaponState(
                    card_id=card_data.get("card_id", ""), name=card_data.get("name", ""),
                    attack=card_data.get("attack", 0), durability=card_data.get("durability", 1))
                player.mana -= card_data.get("mana_cost", 0)
                overload = card_data.get("overload", 0)
                if overload:
                    player.overload += overload
                player.cards_played_this_turn += 1
                log.append(turn_count, state.current_player_idx, "PLAY_WEAPON", card_id,
                           name=card_name, cost=cost)

    elif isinstance(action, Attack):
        player = state.current_player
        opponent = state.opponent
        if action.attacker_idx == -1:
            attacker_name = player.hero.hero_class + " Hero"
            if action.target_is_hero:
                dmg = player.hero.total_attack
                log.append(turn_count, state.current_player_idx, "ATTACK", "hero",
                           target="enemy_hero", damage=dmg, attacker_name=attacker_name)
                engine.hero_attack_hero(state)
            elif action.target_idx < len(opponent.board):
                target = opponent.board[action.target_idx]
                dmg = player.hero.total_attack
                log.append(turn_count, state.current_player_idx, "ATTACK", "hero",
                           target=target.card_id, damage=dmg,
                           attacker_name=attacker_name, target_name=target.name)
                engine.hero_attack_minion(state, opponent.board[action.target_idx])
        elif action.attacker_idx < len(player.board):
            attacker = player.board[action.attacker_idx]
            if action.target_is_hero:
                dmg = attacker.attack
                log.append(turn_count, state.current_player_idx, "ATTACK", attacker.card_id,
                           target="enemy_hero", damage=dmg, attacker_name=attacker.name)
                engine.attack_hero(attacker, opponent.hero, state=state)
            elif action.target_idx < len(opponent.board):
                defender = opponent.board[action.target_idx]
                log.append(turn_count, state.current_player_idx, "ATTACK", attacker.card_id,
                           target=defender.card_id, damage=attacker.attack,
                           attacker_name=attacker.name, target_name=defender.name)
                engine.resolve_combat(attacker, opponent.board[action.target_idx], state=state)

    elif isinstance(action, TradeCard):
        player = state.current_player
        if action.hand_idx < len(player.hand) and player.mana >= 1 and player.deck:
            card_id = player.hand.pop(action.hand_idx)
            card_name = card_db.get(card_id, {}).get("name", card_id)
            log.append(turn_count, state.current_player_idx, "TRADE", card_id,
                       name=card_name)
            player.deck.append(card_id)
            random.shuffle(player.deck)
            player.draw_card()
            player.mana -= 1

    elif isinstance(action, ForgeCard):
        player = state.current_player
        if action.hand_idx < len(player.hand) and player.mana >= 2:
            card_id = player.hand[action.hand_idx]
            card_data = card_db.get(card_id, {})
            card_name = card_data.get("name", card_id)
            log.append(turn_count, state.current_player_idx, "FORGE", card_id,
                       name=card_name)
            forged_id = card_id + "_forged"
            if forged_id not in card_db:
                forged_data = dict(card_data)
                forged_data["card_id"] = forged_id
                forged_data["mechanics"] = [m for m in forged_data.get("mechanics", []) if m != "FORGE"]
                if forged_data.get("card_type") == "MINION":
                    forged_data["attack"] = forged_data.get("attack", 0) + 2
                    forged_data["health"] = forged_data.get("health", 0) + 2
                else:
                    forged_data["mana_cost"] = max(0, forged_data.get("mana_cost", 0) - 1)
                forged_data["name"] = forged_data.get("name", "") + " (Forged)"
                card_db[forged_id] = forged_data
                engine.card_db[forged_id] = forged_data
            player.hand[action.hand_idx] = forged_id
            player.mana -= 2

    elif isinstance(action, HeroPower):
        player = state.current_player
        log.append(turn_count, state.current_player_idx, "HERO_POWER", player.hero.hero_class)
        engine.use_hero_power(state)
