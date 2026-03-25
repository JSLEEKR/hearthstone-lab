from __future__ import annotations
from dataclasses import dataclass, field
import random
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.db.tables import Card


@dataclass
class CardPoolFilter:
    card_type: str | None = None          # "MINION", "SPELL", "WEAPON"
    hero_class: str | None = None         # "MAGE", etc.
    include_neutral: bool = True
    tribe: str | None = None              # "BEAST", "DRAGON", "DEMON", "MECHANICAL", etc.
    min_cost: int | None = None
    max_cost: int | None = None
    exact_cost: int | None = None
    odd_cost: bool | None = None          # True = odd only
    rarity: str | None = None
    mechanic: str | None = None           # has this in mechanics JSON
    collectible: bool = True
    is_standard: bool | None = None
    exclude_card_ids: list[str] = field(default_factory=list)
    spell_school: str | None = None       # "FIRE", "FROST", etc.


class CardPoolManager:
    def __init__(self, db: Session):
        self.db = db
        self._cache: dict[str, list[dict]] = {}

    def _cache_key(self, f: CardPoolFilter) -> str:
        return str(f)

    def query(self, pool_filter: CardPoolFilter) -> list[dict]:
        key = self._cache_key(pool_filter)
        if key in self._cache:
            return self._cache[key]

        q = self.db.query(Card)
        if pool_filter.collectible:
            q = q.filter(Card.collectible == True)
        if pool_filter.card_type:
            q = q.filter(Card.card_type == pool_filter.card_type)
        if pool_filter.hero_class:
            if pool_filter.include_neutral:
                q = q.filter(Card.hero_class.in_([pool_filter.hero_class, "NEUTRAL"]))
            else:
                q = q.filter(Card.hero_class == pool_filter.hero_class)
        if pool_filter.exact_cost is not None:
            q = q.filter(Card.mana_cost == pool_filter.exact_cost)
        if pool_filter.min_cost is not None:
            q = q.filter(Card.mana_cost >= pool_filter.min_cost)
        if pool_filter.max_cost is not None:
            q = q.filter(Card.mana_cost <= pool_filter.max_cost)
        if pool_filter.rarity:
            q = q.filter(Card.rarity == pool_filter.rarity)
        if pool_filter.is_standard is not None:
            q = q.filter(Card.is_standard == pool_filter.is_standard)
        if pool_filter.exclude_card_ids:
            q = q.filter(Card.card_id.notin_(pool_filter.exclude_card_ids))

        cards = q.all()
        results = []
        for c in cards:
            jd = c.json_data or {}
            # Tribe filter
            if pool_filter.tribe:
                card_race = jd.get("race", "")
                card_races = jd.get("races", [])
                if pool_filter.tribe not in ([card_race] + card_races) and "ALL" not in ([card_race] + card_races):
                    continue
            # Mechanic filter
            if pool_filter.mechanic:
                if pool_filter.mechanic not in (c.mechanics or []):
                    continue
            # Odd/even cost filter
            if pool_filter.odd_cost is True and c.mana_cost % 2 == 0:
                continue
            if pool_filter.odd_cost is False and c.mana_cost % 2 == 1:
                continue
            # Spell school filter
            if pool_filter.spell_school:
                if jd.get("spellSchool") != pool_filter.spell_school:
                    continue

            results.append({
                "card_id": c.card_id, "dbf_id": c.dbf_id,
                "name": c.name, "name_ko": c.name_ko,
                "card_type": c.card_type, "hero_class": c.hero_class,
                "mana_cost": c.mana_cost, "attack": c.attack or 0,
                "health": c.health or 0, "rarity": c.rarity,
                "mechanics": c.mechanics or [], "text": c.text or "",
                "race": jd.get("race", ""), "races": jd.get("races", []),
                "spell_school": jd.get("spellSchool", ""),
                "overload": jd.get("overload", 0),
            })

        self._cache[key] = results
        return results

    def random_cards(self, pool_filter: CardPoolFilter, count: int = 1) -> list[dict]:
        pool = self.query(pool_filter)
        if not pool:
            return []
        return [random.choice(pool) for _ in range(count)]

    def discover(self, pool_filter: CardPoolFilter, count: int = 3,
                 class_bonus: str | None = None) -> list[dict]:
        pool = self.query(pool_filter)
        if not pool:
            return []
        if class_bonus:
            weighted = []
            for c in pool:
                weight = 4 if c["hero_class"] == class_bonus else 1
                weighted.extend([c] * weight)
            selected = []
            used_ids = set()
            attempts = 0
            while len(selected) < min(count, len(pool)) and attempts < 100:
                pick = random.choice(weighted)
                if pick["card_id"] not in used_ids:
                    selected.append(pick)
                    used_ids.add(pick["card_id"])
                attempts += 1
            return selected
        return random.sample(pool, min(count, len(pool)))


# Common presets
POOL_PRESETS = {
    "random_minion": CardPoolFilter(card_type="MINION"),
    "random_spell": CardPoolFilter(card_type="SPELL"),
    "random_weapon": CardPoolFilter(card_type="WEAPON"),
    "random_beast": CardPoolFilter(card_type="MINION", tribe="BEAST"),
    "random_dragon": CardPoolFilter(card_type="MINION", tribe="DRAGON"),
    "random_demon": CardPoolFilter(card_type="MINION", tribe="DEMON"),
    "random_mech": CardPoolFilter(card_type="MINION", tribe="MECHANICAL"),
    "random_murloc": CardPoolFilter(card_type="MINION", tribe="MURLOC"),
    "random_elemental": CardPoolFilter(card_type="MINION", tribe="ELEMENTAL"),
    "random_pirate": CardPoolFilter(card_type="MINION", tribe="PIRATE"),
    "random_undead": CardPoolFilter(card_type="MINION", tribe="UNDEAD"),
    "random_naga": CardPoolFilter(card_type="MINION", tribe="NAGA"),
    "random_totem": CardPoolFilter(card_type="MINION", tribe="TOTEM"),
    "random_draenei": CardPoolFilter(card_type="MINION", tribe="DRAENEI"),
    "odd_cost_card": CardPoolFilter(odd_cost=True),
    "even_cost_card": CardPoolFilter(odd_cost=False),
    "random_legendary": CardPoolFilter(rarity="LEGENDARY"),
    "random_legendary_minion": CardPoolFilter(card_type="MINION", rarity="LEGENDARY"),
    "deathrattle_minion": CardPoolFilter(card_type="MINION", mechanic="DEATHRATTLE"),
    "battlecry_minion": CardPoolFilter(card_type="MINION", mechanic="BATTLECRY"),
    "taunt_minion": CardPoolFilter(card_type="MINION", mechanic="TAUNT"),
    "rush_minion": CardPoolFilter(card_type="MINION", mechanic="RUSH"),
    "divine_shield_minion": CardPoolFilter(card_type="MINION", mechanic="DIVINE_SHIELD"),
    "lifesteal_minion": CardPoolFilter(card_type="MINION", mechanic="LIFESTEAL"),
    "random_secret_mage": CardPoolFilter(card_type="SPELL", hero_class="MAGE", mechanic="SECRET", include_neutral=False),
    "random_secret_hunter": CardPoolFilter(card_type="SPELL", hero_class="HUNTER", mechanic="SECRET", include_neutral=False),
    "random_secret_paladin": CardPoolFilter(card_type="SPELL", hero_class="PALADIN", mechanic="SECRET", include_neutral=False),
    "random_secret_rogue": CardPoolFilter(card_type="SPELL", hero_class="ROGUE", mechanic="SECRET", include_neutral=False),
    # Spell school presets
    "fire_spell": CardPoolFilter(card_type="SPELL", spell_school="FIRE"),
    "frost_spell": CardPoolFilter(card_type="SPELL", spell_school="FROST"),
    "shadow_spell": CardPoolFilter(card_type="SPELL", spell_school="SHADOW"),
    "holy_spell": CardPoolFilter(card_type="SPELL", spell_school="HOLY"),
    "nature_spell": CardPoolFilter(card_type="SPELL", spell_school="NATURE"),
    "arcane_spell": CardPoolFilter(card_type="SPELL", spell_school="ARCANE"),
    "fel_spell": CardPoolFilter(card_type="SPELL", spell_school="FEL"),
}
