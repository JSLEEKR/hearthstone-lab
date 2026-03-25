from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class ActionType(str, Enum):
    PLAY_CARD = "PLAY_CARD"
    ATTACK = "ATTACK"
    HERO_POWER = "HERO_POWER"
    END_TURN = "END_TURN"
    TRADE_CARD = "TRADE_CARD"
    FORGE_CARD = "FORGE_CARD"


@dataclass
class PlayCard:
    card_id: str
    hand_idx: int
    target_idx: int | None = None
    target_is_hero: bool = False
    action_type: ActionType = field(default=ActionType.PLAY_CARD, init=False)


@dataclass
class Attack:
    attacker_idx: int
    target_idx: int
    target_is_hero: bool = False
    action_type: ActionType = field(default=ActionType.ATTACK, init=False)


@dataclass
class HeroPower:
    target_idx: int | None = None
    target_is_hero: bool = False
    action_type: ActionType = field(default=ActionType.HERO_POWER, init=False)


@dataclass
class EndTurn:
    action_type: ActionType = field(default=ActionType.END_TURN, init=False)


@dataclass
class TradeCard:
    card_id: str
    hand_idx: int
    action_type: ActionType = field(default=ActionType.TRADE_CARD, init=False)


@dataclass
class ForgeCard:
    card_id: str
    hand_idx: int
    action_type: ActionType = field(default=ActionType.FORGE_CARD, init=False)
