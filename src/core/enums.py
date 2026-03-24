from enum import Enum


class CardType(str, Enum):
    MINION = "MINION"
    SPELL = "SPELL"
    WEAPON = "WEAPON"
    HERO = "HERO"
    HERO_POWER = "HERO_POWER"
    LOCATION = "LOCATION"


class Rarity(str, Enum):
    FREE = "FREE"
    COMMON = "COMMON"
    RARE = "RARE"
    EPIC = "EPIC"
    LEGENDARY = "LEGENDARY"


class HeroClass(str, Enum):
    NEUTRAL = "NEUTRAL"
    MAGE = "MAGE"
    WARRIOR = "WARRIOR"
    PALADIN = "PALADIN"
    HUNTER = "HUNTER"
    ROGUE = "ROGUE"
    PRIEST = "PRIEST"
    SHAMAN = "SHAMAN"
    WARLOCK = "WARLOCK"
    DRUID = "DRUID"
    DEMON_HUNTER = "DEMON_HUNTER"
    DEATH_KNIGHT = "DEATH_KNIGHT"


class GameFormat(str, Enum):
    STANDARD = "standard"
    WILD = "wild"


class Archetype(str, Enum):
    AGGRO = "aggro"
    MIDRANGE = "midrange"
    CONTROL = "control"
    COMBO = "combo"


class MechanicType(str, Enum):
    TAUNT = "TAUNT"
    CHARGE = "CHARGE"
    RUSH = "RUSH"
    DIVINE_SHIELD = "DIVINE_SHIELD"
    STEALTH = "STEALTH"
    LIFESTEAL = "LIFESTEAL"
    POISONOUS = "POISONOUS"
    BATTLECRY = "BATTLECRY"
    DEATHRATTLE = "DEATHRATTLE"
    DISCOVER = "DISCOVER"
    WINDFURY = "WINDFURY"
    REBORN = "REBORN"
    SPELL_DAMAGE = "SPELL_DAMAGE"
    SECRET = "SECRET"
    FREEZE = "FREEZE"
    SILENCE = "SILENCE"
    OVERLOAD = "OVERLOAD"
    COMBO = "COMBO"
    CHOOSE_ONE = "CHOOSE_ONE"
    OUTCAST = "OUTCAST"
    INFUSE = "INFUSE"
    FORGE = "FORGE"
    EXCAVATE = "EXCAVATE"
    TITAN = "TITAN"
    COLOSSAL = "COLOSSAL"
    DORMANT = "DORMANT"
