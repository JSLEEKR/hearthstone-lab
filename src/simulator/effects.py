from __future__ import annotations
import logging
from enum import Enum
from typing import Callable
from src.simulator.game_state import GameState

logger = logging.getLogger(__name__)
EffectFn = Callable[[GameState, dict], None]


class EventType(str, Enum):
    ON_PLAY = "ON_PLAY"
    ON_SUMMON = "ON_SUMMON"
    ON_DEATH = "ON_DEATH"
    ON_DAMAGE = "ON_DAMAGE"
    ON_HEAL = "ON_HEAL"
    ON_TURN_START = "ON_TURN_START"
    ON_TURN_END = "ON_TURN_END"
    ON_DRAW = "ON_DRAW"
    ON_ATTACK = "ON_ATTACK"
    ON_SPELL_CAST = "ON_SPELL_CAST"
    ON_SECRET_REVEAL = "ON_SECRET_REVEAL"


class EffectRegistry:
    def __init__(self):
        self._card_effects: dict[str, dict[EventType, list[EffectFn]]] = {}
        self._global_effects: dict[EventType, list[EffectFn]] = {}

    def register(self, card_id: str, event: EventType, fn: EffectFn):
        if card_id not in self._card_effects:
            self._card_effects[card_id] = {}
        if event not in self._card_effects[card_id]:
            self._card_effects[card_id][event] = []
        self._card_effects[card_id][event].append(fn)

    def register_global(self, event: EventType, fn: EffectFn):
        if event not in self._global_effects:
            self._global_effects[event] = []
        self._global_effects[event].append(fn)

    def trigger(self, event: EventType, state: GameState, ctx: dict):
        card_id = ctx.get("card_id", "")
        for fn in self._card_effects.get(card_id, {}).get(event, []):
            fn(state, ctx)

    def trigger_global(self, event: EventType, state: GameState, ctx: dict):
        for fn in self._global_effects.get(event, []):
            fn(state, ctx)
