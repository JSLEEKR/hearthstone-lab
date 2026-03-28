"""AI Advisor: Provides play recommendations based on current game state."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from helper.game_tracker import LiveGameState, TrackedCard

logger = logging.getLogger(__name__)


@dataclass
class Recommendation:
    action: str  # "PLAY", "ATTACK", "HERO_POWER", "END_TURN"
    card_name: str = ""
    target: str = ""
    reason: str = ""
    priority: int = 0  # higher = do first


class GameAdvisor:
    """Provides AI-powered play recommendations."""

    def __init__(self, card_db: dict | None = None):
        self.card_db = card_db or {}

    def get_recommendations(self, state: LiveGameState) -> list[Recommendation]:
        """Analyze current state and recommend plays."""
        if not state.in_game:
            return []

        recs = []
        available_mana = state.my_mana

        # 1. Check for lethal
        lethal = self._check_lethal(state)
        if lethal:
            return lethal  # If lethal exists, only show lethal line

        # 2. Recommend card plays (mana curve)
        playable = [c for c in state.my_hand if c.cost <= available_mana]
        playable.sort(key=lambda c: -c.cost)  # Highest cost first

        for card in playable:
            reason = self._evaluate_play(card, state)
            recs.append(Recommendation(
                action="PLAY",
                card_name=card.card_name or card.card_id,
                reason=reason,
                priority=self._play_priority(card, state),
            ))

        # 3. Recommend attacks
        for minion in state.my_board:
            if minion.attack > 0:
                target, reason = self._best_attack_target(minion, state)
                recs.append(Recommendation(
                    action="ATTACK",
                    card_name=minion.card_name,
                    target=target,
                    reason=reason,
                    priority=5,
                ))

        # 4. Hero power recommendation
        if available_mana >= 2:
            recs.append(Recommendation(
                action="HERO_POWER",
                reason="Use hero power if no better play",
                priority=1,
            ))

        recs.sort(key=lambda r: -r.priority)
        return recs

    def _check_lethal(self, state: LiveGameState) -> list[Recommendation] | None:
        """Check if lethal damage is available."""
        total_damage = sum(m.attack for m in state.my_board if m.attack > 0)
        # Simplified: doesn't account for taunt
        has_taunt = any(True for m in state.opp_board)  # rough check

        if total_damage >= state.opp_hero_health and not has_taunt:
            recs = []
            for m in state.my_board:
                if m.attack > 0:
                    recs.append(Recommendation(
                        action="ATTACK",
                        card_name=m.card_name,
                        target="FACE",
                        reason="LETHAL! Go face!",
                        priority=100,
                    ))
            return recs
        return None

    def _evaluate_play(self, card: TrackedCard, state: LiveGameState) -> str:
        """Evaluate why a card should be played."""
        if card.card_type == "MINION":
            if not state.my_board:
                return "Develop board presence"
            if card.attack >= 4:
                return "Strong threat"
            return "Curve play"
        elif card.card_type == "SPELL":
            return "Use for tempo/value"
        elif card.card_type == "WEAPON":
            return "Equip for board control"
        return "Playable"

    def _play_priority(self, card: TrackedCard, state: LiveGameState) -> int:
        """Score how urgently this card should be played."""
        score = 10
        # On curve = higher priority
        if card.cost == state.my_mana:
            score += 5
        # Removal spells when opponent has threats
        if card.card_type == "SPELL" and state.opp_board:
            score += 3
        # Minions when board is empty
        if card.card_type == "MINION" and not state.my_board:
            score += 4
        return score

    def _best_attack_target(self, minion: TrackedCard, state: LiveGameState) -> tuple[str, str]:
        """Determine best attack target."""
        # Check for favorable trades
        for opp in state.opp_board:
            if minion.attack >= opp.health and opp.attack >= 3:
                return opp.card_name, f"Kill {opp.card_name} (favorable trade)"

        # If no good trades, go face
        if not state.opp_board:
            return "FACE", "No minions — go face"

        return "FACE", "Push damage"

    def get_deck_stats(self, state: LiveGameState) -> dict:
        """Get deck/hand statistics."""
        return {
            "deck_remaining": state.my_deck_remaining,
            "hand_size": len(state.my_hand),
            "board_size": len(state.my_board),
            "opp_hand": state.opp_hand_count,
            "opp_board": len(state.opp_board),
            "opp_deck": state.opp_deck_remaining,
            "turn": state.turn,
            "opp_cards_seen": len(state.opp_played_cards),
        }

    def get_opponent_profile(self, state: LiveGameState) -> str:
        """Guess opponent's deck archetype from played cards."""
        if not state.opp_played_cards:
            return "Unknown"

        avg_cost = sum(c.cost for c in state.opp_played_cards) / len(state.opp_played_cards)
        if avg_cost <= 2.5:
            return "Aggro"
        elif avg_cost <= 4.0:
            return "Midrange/Tempo"
        else:
            return "Control"
