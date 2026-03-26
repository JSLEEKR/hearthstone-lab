from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class SynergyPackage:
    name: str
    mechanic: str = ""       # e.g., "DEATHRATTLE", "BATTLECRY"
    race: str = ""           # e.g., "DRAGON", "BEAST"
    spell_school: str = ""   # e.g., "FIRE", "FROST"
    card_type: str = ""      # e.g., "SPELL", "MINION"
    keyword: str = ""        # additional keyword filter
    min_cards: int = 6
    max_cards: int = 12
    priority: int = 5        # higher = pick first


@dataclass
class DeckRecipe:
    name: str
    hero_class: str
    archetype: str
    packages: list[SynergyPackage] = field(default_factory=list)
    curve: dict[int, int] = field(default_factory=dict)
    class_card_ratio: float = 0.5  # target ratio of class cards


# Mana curves per archetype
CURVES = {
    "aggro":       {1: 6, 2: 8, 3: 6, 4: 4, 5: 2, 6: 2, 7: 1, 8: 1},
    "midrange":    {1: 3, 2: 5, 3: 6, 4: 6, 5: 4, 6: 3, 7: 2, 8: 1},
    "control":     {1: 2, 2: 4, 3: 4, 4: 4, 5: 4, 6: 4, 7: 4, 8: 4},
    "big":         {1: 1, 2: 3, 3: 3, 4: 3, 5: 4, 6: 4, 7: 6, 8: 6},
    "tempo":       {1: 4, 2: 7, 3: 6, 4: 5, 5: 3, 6: 3, 7: 1, 8: 1},
    "combo":       {1: 3, 2: 5, 3: 5, 4: 4, 5: 4, 6: 4, 7: 3, 8: 2},
    "spell":       {1: 4, 2: 6, 3: 6, 4: 5, 5: 4, 6: 3, 7: 1, 8: 1},
    "token":       {1: 6, 2: 7, 3: 6, 4: 5, 5: 3, 6: 2, 7: 1, 8: 0},
    "deathrattle": {1: 2, 2: 5, 3: 5, 4: 5, 5: 4, 6: 4, 7: 3, 8: 2},
    "dragon":      {1: 2, 2: 4, 3: 5, 4: 5, 5: 4, 6: 4, 7: 3, 8: 3},
    "beast":       {1: 4, 2: 6, 3: 6, 4: 5, 5: 4, 6: 3, 7: 1, 8: 1},
    "undead":      {1: 3, 2: 5, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 2},
    "elemental":   {1: 3, 2: 5, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 2},
    "pirate":      {1: 6, 2: 7, 3: 6, 4: 5, 5: 3, 6: 2, 7: 1, 8: 0},
    "mech":        {1: 3, 2: 6, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1},
}

# Which archetypes are valid for which classes
ARCHETYPE_CLASSES = {
    "aggro":       ["HUNTER", "ROGUE", "DEMON_HUNTER", "PALADIN", "WARRIOR", "SHAMAN"],
    "midrange":    ["HUNTER", "PALADIN", "DRUID", "SHAMAN", "WARRIOR"],
    "control":     ["WARRIOR", "PRIEST", "MAGE", "WARLOCK", "PALADIN"],
    "big":         ["DRUID", "PRIEST", "WARRIOR", "SHAMAN"],
    "tempo":       ["MAGE", "ROGUE", "DEMON_HUNTER", "SHAMAN"],
    "combo":       ["MAGE", "WARLOCK", "DRUID", "ROGUE"],
    "spell":       ["MAGE", "SHAMAN", "DRUID", "PRIEST"],
    "token":       ["DRUID", "PALADIN", "SHAMAN", "WARLOCK"],
    "deathrattle": ["HUNTER", "PRIEST", "ROGUE", "WARLOCK"],
    "dragon":      ["PRIEST", "PALADIN", "WARRIOR", "MAGE"],
    "beast":       ["HUNTER", "DRUID"],
    "undead":      ["PRIEST", "WARLOCK", "DEATH_KNIGHT"],
    "elemental":   ["SHAMAN", "MAGE"],
    "pirate":      ["WARRIOR", "ROGUE"],
    "mech":        ["PALADIN", "WARRIOR", "MAGE", "HUNTER"],
}


def build_recipes(classes: list[str] | None = None,
                  archetypes: list[str] | None = None) -> list[DeckRecipe]:
    """Generate all valid DeckRecipe combinations."""
    recipes = []
    for arch, valid_classes in ARCHETYPE_CLASSES.items():
        if archetypes and arch not in archetypes:
            continue
        curve = CURVES.get(arch, CURVES["midrange"])
        for cls in valid_classes:
            if classes and cls not in classes:
                continue
            packages = _build_packages(arch, cls)
            name = f"{arch.title()} {cls.replace('_', ' ').title()}"
            recipes.append(DeckRecipe(
                name=name,
                hero_class=cls,
                archetype=arch,
                packages=packages,
                curve=dict(curve),
                class_card_ratio=0.45 if arch in ("aggro", "tempo") else 0.5,
            ))
    return recipes


def _build_packages(archetype: str, hero_class: str) -> list[SynergyPackage]:
    """Build synergy packages for a given archetype-class combo."""
    pkgs = []

    # --- Tribal archetypes ---
    tribal_map = {
        "dragon": "DRAGON", "beast": "BEAST", "undead": "UNDEAD",
        "elemental": "ELEMENTAL", "pirate": "PIRATE", "mech": "MECHANICAL",
    }
    if archetype in tribal_map:
        race = tribal_map[archetype]
        pkgs.append(SynergyPackage(name=f"{archetype}_core", race=race,
                                    min_cards=10, max_cards=16, priority=10))

    # --- Mechanic archetypes ---
    if archetype == "deathrattle":
        pkgs.append(SynergyPackage(name="deathrattle_core", mechanic="DEATHRATTLE",
                                    min_cards=8, max_cards=14, priority=10))
    elif archetype == "spell":
        pkgs.append(SynergyPackage(name="spell_core", card_type="SPELL",
                                    min_cards=14, max_cards=20, priority=10))
    elif archetype == "token":
        # Low-cost minions + buff spells
        pkgs.append(SynergyPackage(name="token_minions", card_type="MINION",
                                    min_cards=16, max_cards=22, priority=8))
    elif archetype == "combo":
        pkgs.append(SynergyPackage(name="draw_engine", mechanic="BATTLECRY",
                                    card_type="SPELL", min_cards=8, max_cards=14, priority=8))
    elif archetype == "big":
        # No specific mechanic, just high-cost cards handled by curve
        pass

    # --- Generic archetypes ---
    if archetype == "aggro":
        pkgs.append(SynergyPackage(name="rush_charge", mechanic="RUSH",
                                    min_cards=4, max_cards=8, priority=7))
    elif archetype == "control":
        pkgs.append(SynergyPackage(name="taunt_wall", mechanic="TAUNT",
                                    min_cards=4, max_cards=8, priority=7))
        pkgs.append(SynergyPackage(name="removal", card_type="SPELL",
                                    min_cards=6, max_cards=10, priority=6))

    # Weapon for weapon classes
    weapon_classes = {"WARRIOR", "ROGUE", "PALADIN", "SHAMAN", "DEMON_HUNTER", "HUNTER"}
    if hero_class in weapon_classes and archetype in ("aggro", "tempo", "midrange", "pirate"):
        pkgs.append(SynergyPackage(name="weapons", card_type="WEAPON",
                                    min_cards=1, max_cards=3, priority=5))

    return pkgs
