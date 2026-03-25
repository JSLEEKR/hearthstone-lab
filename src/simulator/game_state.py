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
    mana_cost: int
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
        if self.frozen or self.dormant or self.attack <= 0:
            return False
        max_attacks = 2 if self.windfury else 1
        if self.attacks_this_turn >= max_attacks:
            return False
        if self.summoned_this_turn and not self.charge and not self.rush:
            return False
        return True

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
    hero: HeroState
    mana: int = 0
    max_mana: int = 0
    overload: int = 0
    hand: list[str] = field(default_factory=list)
    board: list[MinionState] = field(default_factory=list)
    deck: list[str] = field(default_factory=list)
    secrets: list[str] = field(default_factory=list)
    fatigue_counter: int = 0

    def draw_card(self) -> str | None:
        if not self.deck:
            self.fatigue_counter += 1
            self.hero.take_damage(self.fatigue_counter)
            return None
        card = self.deck.pop(0)
        if len(self.hand) >= HAND_LIMIT:
            return None
        self.hand.append(card)
        return card

    @property
    def board_full(self) -> bool:
        return len(self.board) >= BOARD_LIMIT


@dataclass
class GameState:
    player1: PlayerState
    player2: PlayerState
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
