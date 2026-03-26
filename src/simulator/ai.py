from __future__ import annotations
import copy
import random
from typing import TYPE_CHECKING
from src.simulator.actions import PlayCard, Attack, HeroPower, EndTurn, TradeCard

if TYPE_CHECKING:
    from src.simulator.engine import GameEngine
    from src.simulator.game_state import GameState

MULLIGAN_COST_THRESHOLD = 3


class BaseAI:
    def choose_action(self, state: GameState, engine: GameEngine):
        raise NotImplementedError

    def mulligan(self, hand: list[str], card_db: dict) -> list[str]:
        return [cid for cid in hand
                if card_db.get(cid, {}).get("mana_cost", 99) <= MULLIGAN_COST_THRESHOLD]


class RuleBasedAI(BaseAI):
    """Level 1: Fast rule-based AI. Plays cards on curve, uses hero power,
    makes efficient trades, and pushes face damage."""

    def choose_action(self, state: GameState, engine: GameEngine):
        actions = engine.get_legal_actions(state)

        # Use hero power BEFORE attacks if it grants attack (Rogue weapon, Druid, DH)
        # so the hero can attack this turn
        hero_powers = [a for a in actions if isinstance(a, HeroPower)]
        hero_class = state.current_player.hero.hero_class
        attack_granting_classes = {"ROGUE", "DRUID", "DEMON_HUNTER"}
        if hero_powers and hero_class in attack_granting_classes:
            return hero_powers[0]

        # Play cards (highest cost first for mana efficiency)
        plays = [a for a in actions if isinstance(a, PlayCard)]
        if plays:
            plays.sort(key=lambda p: engine.card_db.get(p.card_id, {}).get("mana_cost", 0),
                       reverse=True)
            return plays[0]

        # Attack phase: evaluate all attacks and pick best
        attacks = [a for a in actions if isinstance(a, Attack)]
        if attacks:
            return self._best_attack(attacks, state, engine)

        # Use hero power after attacks for non-attack classes (Mage, Hunter, etc.)
        if hero_powers:
            return hero_powers[0]

        return EndTurn()

    def _best_attack(self, attacks: list[Attack], state: GameState,
                     engine: 'GameEngine | None' = None) -> Attack:
        player = state.current_player
        opponent = state.opponent
        opp_hp = opponent.hero.health + opponent.hero.armor
        best = None
        best_score = -9999

        # Calculate total damage we can push to face this turn
        total_board_attack = sum(m.attack for m in player.board if m.can_attack_hero)
        total_board_attack += player.hero.total_attack if player.hero.total_attack > 0 else 0
        can_lethal = total_board_attack >= opp_hp

        for a in attacks:
            if a.attacker_idx == -1:
                atk_value = player.hero.total_attack
                atk_health = 999
            else:
                m = player.board[a.attacker_idx]
                atk_value = m.attack
                atk_health = m.health

            if a.target_is_hero:
                # Face damage scoring: scale with opponent's low health
                if can_lethal:
                    score = 500 + atk_value  # Go for lethal!
                else:
                    # Base face score: proportional to damage dealt
                    # Higher score when opponent is lower HP
                    score = atk_value * 3.0
                    # Bonus when opponent is getting low
                    if opp_hp <= 15:
                        score += atk_value * 2.0
                    if opp_hp <= 10:
                        score += atk_value * 3.0
            else:
                defender = opponent.board[a.target_idx]
                kills = defender.health <= atk_value
                survives = atk_health > defender.attack

                if defender.taunt:
                    # Must kill taunts - high priority
                    if kills and survives:
                        score = 200 + defender.mana_cost
                    elif kills:
                        score = 150 + defender.mana_cost
                    else:
                        score = 80  # still need to hit taunt
                elif kills and survives:
                    # Favorable trade
                    score = 60 + defender.mana_cost * 2
                elif kills:
                    # Even trade
                    score = 30 + defender.mana_cost
                else:
                    # Bad trade - almost never worth it
                    score = -20

            if score > best_score:
                best_score = score
                best = a

        return best or attacks[0]


# Keep SimpleAI as alias for backward compatibility
SimpleAI = RuleBasedAI


class ScoreBasedAI(BaseAI):
    """Level 2: Evaluates board state after each possible action, picks highest score."""

    def choose_action(self, state: GameState, engine: GameEngine):
        from src.simulator.evaluator import evaluate_state
        from src.simulator.match import _execute_action
        from src.simulator.engine import GameEngine as _GameEngine

        actions = engine.get_legal_actions(state)
        player_idx = state.current_player_idx

        best_action = EndTurn()
        best_score = evaluate_state(state, player_idx)

        for action in actions:
            if isinstance(action, EndTurn):
                continue
            try:
                sim_state = copy.deepcopy(state)
                sim_card_db = copy.deepcopy(engine.card_db)
                sim_engine = _GameEngine(card_db=sim_card_db)
                _execute_action(sim_engine, sim_state, action, sim_card_db)
                sim_engine.remove_dead_minions(sim_state)
                score = evaluate_state(sim_state, player_idx)
                if score > best_score:
                    best_score = score
                    best_action = action
            except Exception:
                continue

        return best_action


class MCTSAI(BaseAI):
    """Level 3: Monte Carlo Tree Search AI."""

    def __init__(self, iterations: int = 100, rollout_depth: int = 5):
        self.iterations = iterations
        self.rollout_depth = rollout_depth
        self._rollout_ai = RuleBasedAI()

    def choose_action(self, state: GameState, engine: GameEngine):
        from src.simulator.evaluator import evaluate_state
        from src.simulator.match import _execute_action
        from src.simulator.engine import GameEngine as _GameEngine

        actions = engine.get_legal_actions(state)
        non_end = [a for a in actions if not isinstance(a, EndTurn)]
        if not non_end:
            return EndTurn()

        player_idx = state.current_player_idx
        scores: dict[int, list[float]] = {i: [] for i in range(len(non_end))}

        for _ in range(self.iterations):
            action_idx = random.randint(0, len(non_end) - 1)
            action = non_end[action_idx]
            try:
                sim_state = copy.deepcopy(state)
                sim_card_db = copy.deepcopy(engine.card_db)
                sim_engine = _GameEngine(card_db=sim_card_db)
                _execute_action(sim_engine, sim_state, action, sim_card_db)
                sim_engine.remove_dead_minions(sim_state)

                for _ in range(self.rollout_depth):
                    if sim_state.game_over:
                        break
                    rollout_action = self._rollout_ai.choose_action(sim_state, sim_engine)
                    if isinstance(rollout_action, EndTurn):
                        break
                    _execute_action(sim_engine, sim_state, rollout_action, sim_card_db)
                    sim_engine.remove_dead_minions(sim_state)

                score = evaluate_state(sim_state, player_idx)
                scores[action_idx].append(score)
            except Exception:
                scores[action_idx].append(-500)

        best_idx = 0
        best_avg = -9999.0
        for idx, s_list in scores.items():
            if s_list:
                avg = sum(s_list) / len(s_list)
                if avg > best_avg:
                    best_avg = avg
                    best_idx = idx
        return non_end[best_idx]
