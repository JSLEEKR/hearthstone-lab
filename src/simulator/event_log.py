from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class GameEvent:
    turn: int
    player_idx: int
    event_type: str  # DRAW, PLAY_MINION, PLAY_SPELL, PLAY_WEAPON, ATTACK, DAMAGE, HEAL, DEATH, HERO_POWER, FATIGUE, FREEZE, DISCOVER, etc.
    source: str       # card_id or "hero" or "fatigue"
    target: str | None = None
    details: dict = field(default_factory=dict)


class GameEventLog:
    def __init__(self):
        self.events: list[GameEvent] = []

    def append(self, turn: int, player_idx: int, event_type: str,
               source: str, target: str | None = None, **details):
        self.events.append(GameEvent(
            turn=turn, player_idx=player_idx, event_type=event_type,
            source=source, target=target, details=details,
        ))

    def get_turn(self, turn: int) -> list[GameEvent]:
        return [e for e in self.events if e.turn == turn]

    def format_event(self, event: GameEvent) -> str:
        p = f"P{event.player_idx + 1}"
        t = f"T{event.turn}"
        det = " ".join(f"{k}={v}" for k, v in event.details.items())
        target_str = f" -> {event.target}" if event.target else ""
        return f"[{t}][{p}] {event.event_type}: {event.source}{target_str} {det}"

    def format_all(self) -> str:
        return "\n".join(self.format_event(e) for e in self.events)

    def to_dicts(self) -> list[dict]:
        return [
            {"turn": e.turn, "player": e.player_idx, "type": e.event_type,
             "source": e.source, "target": e.target, **e.details}
            for e in self.events
        ]
