from __future__ import annotations
from dataclasses import dataclass, field

HAND_LIMIT = 10
BOARD_LIMIT = 7


@dataclass
class MinionState:
    card_id: str
    name: str
    attack: int
    health: int
    max_health: int
    mana_cost: int = 0
    taunt: bool = False
    divine_shield: bool = False
    stealth: bool = False
    windfury: bool = False
    lifesteal: bool = False
    poisonous: bool = False
    reborn: bool = False
    rush: bool = False
    charge: bool = False
    frozen: bool = False
    dormant: bool = False
    attacks_this_turn: int = 0
    summoned_this_turn: bool = True
    enrage_bonus: int = 0
    aura_attack_bonus: int = 0
    frenzy_triggered: bool = False
    spellburst_active: bool = False
    titan_turns_remaining: int = 0
    titan_abilities_used: list[bool] = field(default_factory=lambda: [False, False, False])
    mechanics: list[str] = field(default_factory=list)

    def take_damage(self, amount: int) -> int:
        if self.divine_shield and amount > 0:
            self.divine_shield = False
            return 0
        self.health -= amount
        return amount

    @property
    def is_dead(self) -> bool:
        return self.health <= 0

    @property
    def can_attack(self) -> bool:
        if "CANT_ATTACK" in self.mechanics:
            return False
        if self.titan_turns_remaining > 0:
            return False
        if self.frozen or self.dormant or self.attack <= 0:
            return False
        max_attacks = 2 if self.windfury else 1
        if self.attacks_this_turn >= max_attacks:
            return False
        if self.summoned_this_turn and not self.charge and not self.rush:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "card_id": self.card_id, "name": self.name,
            "attack": self.attack, "health": self.health, "max_health": self.max_health,
            "taunt": self.taunt, "divine_shield": self.divine_shield,
            "stealth": self.stealth, "poisonous": self.poisonous,
            "lifesteal": self.lifesteal, "reborn": self.reborn,
            "rush": self.rush, "charge": self.charge, "frozen": self.frozen,
            "windfury": self.windfury, "mechanics": self.mechanics,
        }

    @property
    def can_attack_minions(self) -> bool:
        if not self.can_attack:
            return False
        return True

    @property
    def can_attack_hero(self) -> bool:
        if not self.can_attack:
            return False
        if self.summoned_this_turn and self.rush and not self.charge:
            return False
        return True


@dataclass
class WeaponState:
    card_id: str
    name: str
    attack: int
    durability: int

    @property
    def is_broken(self) -> bool:
        return self.durability <= 0


@dataclass
class HeroState:
    hero_class: str
    health: int = 30
    max_health: int = 30
    armor: int = 0
    attack: int = 0
    hero_power_cost: int = 2
    hero_power_used: bool = False
    frozen: bool = False
    attacks_this_turn: int = 0
    weapon: WeaponState | None = None

    def take_damage(self, amount: int) -> int:
        if self.armor >= amount:
            self.armor -= amount
            return amount
        remaining = amount - self.armor
        self.armor = 0
        self.health -= remaining
        return amount

    def to_dict(self) -> dict:
        return {
            "hero_class": self.hero_class, "health": self.health,
            "armor": self.armor, "attack": self.attack,
            "weapon": {"attack": self.weapon.attack, "durability": self.weapon.durability} if self.weapon else None,
        }

    @property
    def is_dead(self) -> bool:
        return self.health <= 0

    @property
    def total_attack(self) -> int:
        base = self.attack
        if self.weapon and not self.weapon.is_broken:
            base += self.weapon.attack
        return base


@dataclass
class PlayerState:
    hero: HeroState = field(default_factory=lambda: HeroState(hero_class="NEUTRAL"))
    mana: int = 0
    max_mana: int = 0
    overload: int = 0
    hand: list[str] = field(default_factory=list)
    board: list[MinionState] = field(default_factory=list)
    deck: list[str] = field(default_factory=list)
    secrets: list[str] = field(default_factory=list)
    fatigue_counter: int = 0
    cards_played_this_turn: int = 0
    friendly_deaths_this_game: int = 0
    echo_cards: list[str] = field(default_factory=list)
    corrupted_cards: dict[str, bool] = field(default_factory=dict)
    jade_counter: int = 0
    drawn_this_turn: list[str] = field(default_factory=list)
    herald_count: int = 0
    quest_progress: int = 0
    quest_threshold: int = 0
    quest_reward_given: bool = False
    active_quest: str = ""
    starship_parts: int = 0
    graveyard: list[str] = field(default_factory=list)
    burned_cards: list[str] = field(default_factory=list)
    played_cards_this_game: list[dict] = field(default_factory=list)  # [{card_id, card_type, mana_cost, turn, mechanics, race}]
    spells_cast_this_turn: list[str] = field(default_factory=list)  # card_ids of spells cast this turn
    spells_cast_last_turn: list[str] = field(default_factory=list)  # card_ids from previous turn
    hero_hp_at_turn_start: int = 0  # hero HP + armor snapshot at turn start
    corpses: int = 0  # Death Knight corpse resource
    next_battlecry_multiplier: int = 1  # 1 = normal, 3 = Shudderblock
    next_spell_cast_twice_count: int = 0  # Tyrande: how many more spells cast twice

    def draw_card(self) -> str | None:
        if not self.deck:
            self.fatigue_counter += 1
            self.hero.take_damage(self.fatigue_counter)
            return None
        card = self.deck.pop(0)
        if len(self.hand) >= HAND_LIMIT:
            self.burned_cards.append(card)
            return None
        self.hand.append(card)
        self.drawn_this_turn.append(card)
        return card

    def to_dict(self) -> dict:
        return {
            "hero": self.hero.to_dict(), "mana": self.mana, "max_mana": self.max_mana,
            "hand_size": len(self.hand), "deck_size": len(self.deck),
            "board": [m.to_dict() for m in self.board],
            "fatigue_counter": self.fatigue_counter,
        }

    @property
    def board_full(self) -> bool:
        return len(self.board) >= BOARD_LIMIT


@dataclass
class GameState:
    player1: PlayerState = field(default_factory=PlayerState)
    player2: PlayerState = field(default_factory=PlayerState)
    turn: int = 0
    current_player_idx: int = 0

    @property
    def current_player(self) -> PlayerState:
        return self.player1 if self.current_player_idx == 0 else self.player2

    @property
    def opponent(self) -> PlayerState:
        return self.player2 if self.current_player_idx == 0 else self.player1

    def switch_turn(self):
        self.current_player_idx = 1 - self.current_player_idx
        self.turn += 1

    def to_dict(self) -> dict:
        return {
            "turn": self.turn, "current_player_idx": self.current_player_idx,
            "player1": self.player1.to_dict(), "player2": self.player2.to_dict(),
            "game_over": self.game_over,
        }

    @property
    def game_over(self) -> bool:
        return self.player1.hero.is_dead or self.player2.hero.is_dead

    @property
    def winner_idx(self) -> int | None:
        if self.player1.hero.is_dead and self.player2.hero.is_dead:
            return None
        if self.player1.hero.is_dead:
            return 1
        if self.player2.hero.is_dead:
            return 0
        return None
