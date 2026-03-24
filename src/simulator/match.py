from __future__ import annotations
import random
import logging
from dataclasses import dataclass
from src.simulator.ai import SimpleAI
from src.simulator.engine import GameEngine
from src.simulator.game_state import GameState, PlayerState, HeroState, WeaponState
from src.simulator.actions import PlayCard, Attack, HeroPower, EndTurn

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    winner: str | None  # "A", "B", or None
    turns: int


def run_match(deck_a: list[str], deck_b: list[str], hero_a: str, hero_b: str,
              card_db: dict, max_turns: int = 45) -> MatchResult:
    engine = GameEngine(card_db=card_db)
    ai = SimpleAI()

    state = GameState(
        player1=PlayerState(hero=HeroState(hero_class=hero_a), deck=list(deck_a)),
        player2=PlayerState(hero=HeroState(hero_class=hero_b), deck=list(deck_b)),
    )

    engine.start_game(state)

    keep_1 = ai.mulligan(state.player1.hand, card_db)
    _do_mulligan(state.player1, keep_1)

    keep_2 = ai.mulligan(state.player2.hand, card_db)
    _do_mulligan(state.player2, keep_2)

    turn_count = 0
    while not state.game_over and turn_count < max_turns:
        engine.start_turn(state)
        turn_count += 1

        action_count = 0
        while action_count < 50:
            action = ai.choose_action(state, engine)
            if isinstance(action, EndTurn):
                break
            _execute_action(engine, state, action, card_db)
            engine.remove_dead_minions(state)
            if state.game_over:
                break
            action_count += 1

        if state.game_over:
            break
        engine.end_turn(state)

    winner = None
    if state.game_over:
        if state.winner_idx == 0:
            winner = "A"
        elif state.winner_idx == 1:
            winner = "B"

    return MatchResult(winner=winner, turns=turn_count)


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


def _execute_action(engine: GameEngine, state: GameState, action, card_db: dict):
    if isinstance(action, PlayCard):
        player = state.current_player
        if action.hand_idx < len(player.hand):
            card_id = player.hand.pop(action.hand_idx)
            card_data = card_db.get(card_id, {})
            card_type = card_data.get("card_type", "MINION")
            if card_type == "MINION":
                engine.play_minion(state, card_data)
            elif card_type == "SPELL":
                engine.play_spell(state, card_data)
            elif card_type == "WEAPON":
                player.hero.weapon = WeaponState(
                    card_id=card_data.get("card_id", ""), name=card_data.get("name", ""),
                    attack=card_data.get("attack", 0), durability=card_data.get("durability", 1))
                player.mana -= card_data.get("mana_cost", 0)
    elif isinstance(action, Attack):
        player = state.current_player
        opponent = state.opponent
        if action.attacker_idx < len(player.board):
            attacker = player.board[action.attacker_idx]
            if action.target_is_hero:
                engine.attack_hero(attacker, opponent.hero)
            elif action.target_idx < len(opponent.board):
                engine.resolve_combat(attacker, opponent.board[action.target_idx])
    elif isinstance(action, HeroPower):
        engine.use_hero_power(state)
