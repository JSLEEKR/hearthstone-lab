"""Per-card performance statistics tracking during match simulation."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class CardPerformanceRecord:
    """Cumulative stats for one card across multiple games."""
    card_id: str
    games_in_deck: int = 0
    times_drawn: int = 0
    times_played: int = 0
    times_kept_mulligan: int = 0
    times_seen_mulligan: int = 0
    turns_played: list[int] = field(default_factory=list)
    score_deltas: list[float] = field(default_factory=list)  # board impact per play
    wins_when_drawn: int = 0
    games_drawn: int = 0
    wins_when_not_drawn: int = 0
    games_not_drawn: int = 0
    dead_card_games: int = 0  # games where card sat 3+ turns unplayed after draw

    @property
    def play_rate(self) -> float:
        return min(self.times_played / max(self.times_drawn, 1), 1.0)

    @property
    def drawn_winrate(self) -> float:
        return self.wins_when_drawn / max(self.games_drawn, 1)

    @property
    def not_drawn_winrate(self) -> float:
        return self.wins_when_not_drawn / max(self.games_not_drawn, 1)

    @property
    def drawn_winrate_delta(self) -> float:
        """Positive = drawing this card helps. Negative = hurts."""
        return self.drawn_winrate - self.not_drawn_winrate

    @property
    def mulligan_keep_rate(self) -> float:
        return self.times_kept_mulligan / max(self.times_seen_mulligan, 1)

    @property
    def avg_turn_played(self) -> float:
        return sum(self.turns_played) / max(len(self.turns_played), 1)

    @property
    def avg_board_impact(self) -> float:
        return sum(self.score_deltas) / max(len(self.score_deltas), 1)

    @property
    def dead_card_rate(self) -> float:
        return self.dead_card_games / max(self.games_drawn, 1)

    @property
    def underperformance_score(self) -> float:
        """Higher = worse. Used to rank cards for replacement."""
        return (
            max(0, -self.drawn_winrate_delta) * 40
            + (1 - self.play_rate) * 20
            + self.dead_card_rate * 20
            + max(0, -self.avg_board_impact) * 20
        )


class GameCardTracker:
    """Tracks card events during a single game for one player."""

    def __init__(self, deck_card_ids: list[str]):
        self.deck_set = set(deck_card_ids)
        self.drawn_count: dict[str, int] = {}  # card_id -> number of times drawn
        self.played: list[tuple[str, int]] = []  # (card_id, turn)
        self.hand_draw_turn: dict[str, int] = {}  # card_id -> turn drawn
        self.mulligan_offered: list[str] = []
        self.mulligan_kept: list[str] = []
        self.score_deltas: dict[str, list[float]] = {}  # card_id -> [deltas]
        self.dead_cards: set[str] = set()

    def on_draw(self, card_id: str, turn: int):
        if card_id in self.deck_set:
            self.drawn_count[card_id] = self.drawn_count.get(card_id, 0) + 1
            if card_id not in self.hand_draw_turn:
                self.hand_draw_turn[card_id] = turn

    def on_play(self, card_id: str, turn: int, score_before: float, score_after: float):
        if card_id in self.deck_set:
            self.played.append((card_id, turn))
            self.score_deltas.setdefault(card_id, []).append(score_after - score_before)
            self.hand_draw_turn.pop(card_id, None)

    def on_turn_end(self, turn: int):
        # Check for dead cards (in hand 3+ turns without being played)
        for card_id, draw_turn in list(self.hand_draw_turn.items()):
            if turn - draw_turn >= 3:
                self.dead_cards.add(card_id)

    def on_mulligan(self, offered: list[str], kept: list[str]):
        self.mulligan_offered = [c for c in offered if c in self.deck_set]
        self.mulligan_kept = [c for c in kept if c in self.deck_set]

    def finalize(self, won: bool, records: dict[str, CardPerformanceRecord]):
        """Flush this game's data into cumulative records."""
        for card_id in self.deck_set:
            if card_id not in records:
                records[card_id] = CardPerformanceRecord(card_id=card_id)
            rec = records[card_id]
            rec.games_in_deck += 1

            draw_count = self.drawn_count.get(card_id, 0)
            was_drawn = draw_count > 0
            if was_drawn:
                rec.times_drawn += draw_count
                rec.games_drawn += 1
                if won:
                    rec.wins_when_drawn += 1
                if card_id in self.dead_cards:
                    rec.dead_card_games += 1
            else:
                rec.games_not_drawn += 1
                if won:
                    rec.wins_when_not_drawn += 1

            # Played?
            for played_id, turn in self.played:
                if played_id == card_id:
                    rec.times_played += 1
                    rec.turns_played.append(turn)

            # Score deltas
            for delta in self.score_deltas.get(card_id, []):
                rec.score_deltas.append(delta)

            # Mulligan
            if card_id in self.mulligan_offered:
                rec.times_seen_mulligan += 1
                if card_id in self.mulligan_kept:
                    rec.times_kept_mulligan += 1
