from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from src.core.enums import (
    Archetype, CardType, GameFormat, HeroClass, Rarity,
)


class CardData(BaseModel):
    card_id: str
    dbf_id: int
    name: str
    name_ko: str
    card_type: CardType
    hero_class: HeroClass
    mana_cost: int
    attack: int | None = None
    health: int | None = None
    durability: int | None = None
    text: str = ""
    rarity: Rarity
    set_name: str
    mechanics: list[str] = Field(default_factory=list)
    collectible: bool = True
    is_standard: bool = False
    image_url: str = ""
    json_data: dict | None = None

    @field_validator("mana_cost")
    @classmethod
    def mana_cost_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("mana_cost must be >= 0")
        return v


class DeckData(BaseModel):
    name: str
    hero_class: HeroClass
    format: GameFormat
    archetype: Archetype | None = None
    cards: dict[str, int] = Field(default_factory=dict)
    deckstring: str | None = None
    source: str = "manual"

    @property
    def total_cards(self) -> int:
        return sum(self.cards.values())
