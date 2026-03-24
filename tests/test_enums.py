from src.core.enums import (
    CardType, Rarity, HeroClass, GameFormat, Archetype, MechanicType,
)


def test_card_type_values():
    assert CardType.MINION.value == "MINION"
    assert CardType.SPELL.value == "SPELL"
    assert CardType.WEAPON.value == "WEAPON"
    assert CardType.HERO.value == "HERO"


def test_rarity_values():
    assert Rarity.FREE.value == "FREE"
    assert Rarity.COMMON.value == "COMMON"
    assert Rarity.RARE.value == "RARE"
    assert Rarity.EPIC.value == "EPIC"
    assert Rarity.LEGENDARY.value == "LEGENDARY"


def test_hero_class_values():
    assert HeroClass.NEUTRAL.value == "NEUTRAL"
    assert HeroClass.MAGE.value == "MAGE"
    assert HeroClass.WARRIOR.value == "WARRIOR"
    assert HeroClass.PALADIN.value == "PALADIN"
    assert HeroClass.HUNTER.value == "HUNTER"
    assert HeroClass.ROGUE.value == "ROGUE"
    assert HeroClass.PRIEST.value == "PRIEST"
    assert HeroClass.SHAMAN.value == "SHAMAN"
    assert HeroClass.WARLOCK.value == "WARLOCK"
    assert HeroClass.DRUID.value == "DRUID"
    assert HeroClass.DEMON_HUNTER.value == "DEMON_HUNTER"
    assert HeroClass.DEATH_KNIGHT.value == "DEATH_KNIGHT"


def test_game_format_values():
    assert GameFormat.STANDARD.value == "standard"
    assert GameFormat.WILD.value == "wild"


def test_archetype_values():
    assert Archetype.AGGRO.value == "aggro"
    assert Archetype.MIDRANGE.value == "midrange"
    assert Archetype.CONTROL.value == "control"
    assert Archetype.COMBO.value == "combo"


def test_mechanic_type_has_key_mechanics():
    assert MechanicType.TAUNT.value == "TAUNT"
    assert MechanicType.CHARGE.value == "CHARGE"
    assert MechanicType.RUSH.value == "RUSH"
    assert MechanicType.DIVINE_SHIELD.value == "DIVINE_SHIELD"
    assert MechanicType.STEALTH.value == "STEALTH"
    assert MechanicType.LIFESTEAL.value == "LIFESTEAL"
    assert MechanicType.POISONOUS.value == "POISONOUS"
    assert MechanicType.BATTLECRY.value == "BATTLECRY"
    assert MechanicType.DEATHRATTLE.value == "DEATHRATTLE"
    assert MechanicType.DISCOVER.value == "DISCOVER"
    assert MechanicType.WINDFURY.value == "WINDFURY"
    assert MechanicType.REBORN.value == "REBORN"
    assert MechanicType.SPELL_DAMAGE.value == "SPELL_DAMAGE"
    assert MechanicType.SECRET.value == "SECRET"
    assert MechanicType.FREEZE.value == "FREEZE"
    assert MechanicType.SILENCE.value == "SILENCE"
    assert MechanicType.OVERLOAD.value == "OVERLOAD"
    assert MechanicType.COMBO.value == "COMBO"
    assert MechanicType.CHOOSE_ONE.value == "CHOOSE_ONE"
    assert MechanicType.OUTCAST.value == "OUTCAST"
    assert MechanicType.INFUSE.value == "INFUSE"
    assert MechanicType.FORGE.value == "FORGE"
    assert MechanicType.EXCAVATE.value == "EXCAVATE"
    assert MechanicType.TITAN.value == "TITAN"
    assert MechanicType.COLOSSAL.value == "COLOSSAL"
    assert MechanicType.DORMANT.value == "DORMANT"
