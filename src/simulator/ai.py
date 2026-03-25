from __future__ import annotations
from typing import TYPE_CHECKING
from src.simulator.actions import PlayCard, Attack, HeroPower, EndTurn

if TYPE_CHECKING:
    from src.simulator.engine import GameEngine
    from src.simulator.game_state import GameState

MULLIGAN_COST_THRESHOLD = 3


class SimpleAI:
    def choose_action(self, state: GameState, engine: GameEngine):
        actions = engine.get_legal_actions(state)

        attacks = [a for a in actions if isinstance(a, Attack)]
        if attacks:
            return self._best_attack(attacks, state)

        plays = [a for a in actions if isinstance(a, PlayCard)]
        if plays:
            plays.sort(key=lambda p: engine.card_db.get(p.card_id, {}).get("mana_cost", 0), reverse=True)
            return plays[0]

        hero_powers = [a for a in actions if isinstance(a, HeroPower)]
        if hero_powers:
            return hero_powers[0]

        return EndTurn()

    def _best_attack(self, attacks: list[Attack], state: GameState) -> Attack:
        player = state.current_player
        opponent = state.opponent
        best = None
        best_score = -999

        for a in attacks:
            # Determine attacker's attack value
            if a.attacker_idx == -1:
                atk_value = player.hero.total_attack
            else:
                atk_value = player.board[a.attacker_idx].attack

            if a.target_is_hero:
                score = atk_value
            else:
                defender = opponent.board[a.target_idx]
                if defender.health <= atk_value:
                    score = defender.mana_cost + 10
                    if defender.taunt:
                        score += 20
                else:
                    score = 0
            if score > best_score:
                best_score = score
                best = a
        return best or attacks[0]

    def mulligan(self, hand: list[str], card_db: dict) -> list[str]:
        return [cid for cid in hand if card_db.get(cid, {}).get("mana_cost", 99) <= MULLIGAN_COST_THRESHOLD]
