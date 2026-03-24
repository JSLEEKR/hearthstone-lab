# Sub-Project 3: Game Simulation Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Hearthstone game simulation engine that can run automated matches between two AI-controlled decks, with an event-based card effect system and MCTS-based AI decision making.

**Architecture:** Self-contained engine referencing Fireplace's design patterns. Event-driven effect system with EffectRegistry. MCTS AI with rule-based heuristic fallback. Match runner with configurable iterations.

**Tech Stack:** Python 3.11+, dataclasses, enum, random, multiprocessing

**Spec:** `docs/superpowers/specs/2026-03-24-hearthstone-deckmaker-design.md`

---

## File Structure

```
src/
├── core/
│   └── models.py          # Add PlayerState, GameState (extend existing)
└── simulator/
    ├── __init__.py
    ├── game_state.py      # GameState, PlayerState, MinionState, WeaponState
    ├── actions.py         # Action types: PlayCard, Attack, HeroPower, EndTurn
    ├── engine.py          # Game engine: turn loop, combat, spell resolution
    ├── effects.py         # Event system + EffectRegistry + keyword implementations
    ├── ai.py              # MCTS AI + rule-based heuristics + mulligan strategy
    └── match.py           # Match runner: deck vs deck, N iterations, DB recording

tests/
├── test_game_state.py
├── test_actions.py
├── test_engine.py
├── test_effects.py
├── test_ai.py
└── test_match.py
```

---

### Task 1: Game state models

**Files:**
- Create: `src/simulator/game_state.py`
- Create: `tests/test_game_state.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_game_state.py
import pytest
from src.simulator.game_state import (
    MinionState, WeaponState, PlayerState, GameState, HeroState,
)


class TestMinionState:
    def test_create_minion(self):
        m = MinionState(card_id="CS2_182", name="Chillwind Yeti",
                        attack=4, health=5, max_health=5, mana_cost=4)
        assert m.attack == 4
        assert m.health == 5
        assert m.can_attack is False  # summoning sickness

    def test_minion_take_damage(self):
        m = MinionState(card_id="CS2_182", name="Yeti",
                        attack=4, health=5, max_health=5, mana_cost=4)
        m.take_damage(3)
        assert m.health == 2
        assert m.is_dead is False

    def test_minion_dies_at_zero(self):
        m = MinionState(card_id="CS2_182", name="Yeti",
                        attack=4, health=5, max_health=5, mana_cost=4)
        m.take_damage(5)
        assert m.health == 0
        assert m.is_dead is True

    def test_minion_with_taunt(self):
        m = MinionState(card_id="CS2_125", name="Sen'jin",
                        attack=3, health=5, max_health=5, mana_cost=4,
                        taunt=True)
        assert m.taunt is True

    def test_minion_with_rush_can_attack_minions(self):
        m = MinionState(card_id="TEST", name="Rusher",
                        attack=3, health=3, max_health=3, mana_cost=3,
                        rush=True)
        assert m.can_attack_minions is True
        assert m.can_attack_hero is False

    def test_minion_with_charge_can_attack_immediately(self):
        m = MinionState(card_id="TEST", name="Charger",
                        attack=4, health=2, max_health=2, mana_cost=4,
                        charge=True)
        assert m.can_attack is True


class TestHeroState:
    def test_default_hero(self):
        h = HeroState(hero_class="MAGE")
        assert h.health == 30
        assert h.armor == 0
        assert h.hero_power_cost == 2
        assert h.hero_power_used is False

    def test_hero_take_damage_with_armor(self):
        h = HeroState(hero_class="WARRIOR", armor=5)
        h.take_damage(7)
        assert h.armor == 0
        assert h.health == 28


class TestPlayerState:
    def test_initial_state(self):
        p = PlayerState(hero=HeroState(hero_class="MAGE"))
        assert p.mana == 0
        assert p.max_mana == 0
        assert len(p.hand) == 0
        assert len(p.board) == 0
        assert p.fatigue_counter == 0

    def test_draw_from_deck(self):
        p = PlayerState(hero=HeroState(hero_class="MAGE"))
        p.deck = ["card1", "card2", "card3"]
        drawn = p.draw_card()
        assert drawn == "card1"
        assert len(p.deck) == 2

    def test_draw_fatigue_when_empty(self):
        p = PlayerState(hero=HeroState(hero_class="MAGE"))
        p.deck = []
        drawn = p.draw_card()
        assert drawn is None
        assert p.fatigue_counter == 1
        assert p.hero.health == 29  # 1 fatigue damage

    def test_hand_limit_10(self):
        p = PlayerState(hero=HeroState(hero_class="MAGE"))
        p.hand = [f"card_{i}" for i in range(10)]
        p.deck = ["overflow"]
        drawn = p.draw_card()
        assert drawn is None  # burned
        assert len(p.hand) == 10

    def test_board_limit_7(self):
        p = PlayerState(hero=HeroState(hero_class="MAGE"))
        for i in range(7):
            p.board.append(MinionState(card_id=f"m{i}", name=f"m{i}",
                           attack=1, health=1, max_health=1, mana_cost=1))
        assert p.board_full is True


class TestGameState:
    def test_create_game(self):
        g = GameState(
            player1=PlayerState(hero=HeroState(hero_class="MAGE")),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        assert g.turn == 0
        assert g.current_player_idx == 0
        assert g.game_over is False

    def test_switch_turn(self):
        g = GameState(
            player1=PlayerState(hero=HeroState(hero_class="MAGE")),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        g.switch_turn()
        assert g.current_player_idx == 1
        assert g.turn == 1

    def test_game_over_when_hero_dies(self):
        g = GameState(
            player1=PlayerState(hero=HeroState(hero_class="MAGE")),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        g.player1.hero.health = 0
        assert g.game_over is True
        assert g.winner_idx == 1
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Write implementation**

```python
# src/simulator/game_state.py
from __future__ import annotations
from dataclasses import dataclass, field


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


HAND_LIMIT = 10
BOARD_LIMIT = 7


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
            return None  # card burned
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
            return None  # draw
        if self.player1.hero.is_dead:
            return 1
        if self.player2.hero.is_dead:
            return 0
        return None
```

- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add game state models (minion, hero, player, game state)"
```

---

### Task 2: Action types

**Files:**
- Create: `src/simulator/actions.py`
- Create: `tests/test_actions.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_actions.py
from src.simulator.actions import (
    PlayCard, Attack, HeroPower, EndTurn, ActionType,
)


def test_play_card_action():
    a = PlayCard(card_id="CS2_029", hand_idx=0, target_idx=None)
    assert a.action_type == ActionType.PLAY_CARD
    assert a.card_id == "CS2_029"


def test_attack_action():
    a = Attack(attacker_idx=0, target_idx=1, target_is_hero=False)
    assert a.action_type == ActionType.ATTACK


def test_hero_power_action():
    a = HeroPower(target_idx=None)
    assert a.action_type == ActionType.HERO_POWER


def test_end_turn_action():
    a = EndTurn()
    assert a.action_type == ActionType.END_TURN
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write implementation**

```python
# src/simulator/actions.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class ActionType(str, Enum):
    PLAY_CARD = "PLAY_CARD"
    ATTACK = "ATTACK"
    HERO_POWER = "HERO_POWER"
    END_TURN = "END_TURN"


@dataclass
class PlayCard:
    card_id: str
    hand_idx: int
    target_idx: int | None = None
    action_type: ActionType = ActionType.PLAY_CARD


@dataclass
class Attack:
    attacker_idx: int
    target_idx: int
    target_is_hero: bool = False
    action_type: ActionType = ActionType.ATTACK


@dataclass
class HeroPower:
    target_idx: int | None = None
    action_type: ActionType = ActionType.HERO_POWER


@dataclass
class EndTurn:
    action_type: ActionType = ActionType.END_TURN
```

- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add action types for game simulation"
```

---

### Task 3: Game engine core

**Files:**
- Create: `src/simulator/engine.py`
- Create: `tests/test_engine.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_engine.py
import pytest
from src.simulator.game_state import (
    GameState, PlayerState, HeroState, MinionState,
)
from src.simulator.engine import GameEngine


def _make_game(
    p1_deck: list[str] | None = None,
    p2_deck: list[str] | None = None,
) -> GameState:
    return GameState(
        player1=PlayerState(
            hero=HeroState(hero_class="MAGE"),
            deck=list(p1_deck or [f"card_{i}" for i in range(30)]),
        ),
        player2=PlayerState(
            hero=HeroState(hero_class="WARRIOR"),
            deck=list(p2_deck or [f"card_{i}" for i in range(30)]),
        ),
    )


class TestGameEngine:
    def test_start_game_draws_cards(self):
        engine = GameEngine()
        state = _make_game()
        engine.start_game(state)
        # Player 1 (going first) draws 3, Player 2 draws 4
        assert len(state.player1.hand) == 3
        assert len(state.player2.hand) == 4

    def test_start_turn_gives_mana(self):
        engine = GameEngine()
        state = _make_game()
        engine.start_game(state)
        engine.start_turn(state)
        assert state.current_player.max_mana == 1
        assert state.current_player.mana == 1

    def test_mana_caps_at_10(self):
        engine = GameEngine()
        state = _make_game()
        state.current_player.max_mana = 10
        engine.start_turn(state)
        assert state.current_player.max_mana == 10
        assert state.current_player.mana == 10

    def test_start_turn_draws_card(self):
        engine = GameEngine()
        state = _make_game()
        engine.start_game(state)
        initial_hand = len(state.current_player.hand)
        engine.start_turn(state)
        assert len(state.current_player.hand) == initial_hand + 1

    def test_minion_combat(self):
        engine = GameEngine()
        state = _make_game()
        m1 = MinionState(card_id="a", name="A", attack=3, health=5,
                         max_health=5, mana_cost=3, summoned_this_turn=False)
        m2 = MinionState(card_id="b", name="B", attack=2, health=4,
                         max_health=4, mana_cost=2)
        state.player1.board.append(m1)
        state.player2.board.append(m2)

        engine.resolve_combat(m1, m2)
        assert m1.health == 3  # took 2 damage
        assert m2.health == 1  # took 3 damage

    def test_hero_attack(self):
        engine = GameEngine()
        state = _make_game()
        m1 = MinionState(card_id="a", name="A", attack=5, health=2,
                         max_health=2, mana_cost=2, summoned_this_turn=False)
        state.player1.board.append(m1)

        engine.attack_hero(m1, state.player2.hero)
        assert state.player2.hero.health == 25

    def test_dead_minions_removed(self):
        engine = GameEngine()
        state = _make_game()
        m1 = MinionState(card_id="a", name="A", attack=4, health=1,
                         max_health=1, mana_cost=1, summoned_this_turn=False)
        m2 = MinionState(card_id="b", name="B", attack=4, health=1,
                         max_health=1, mana_cost=1)
        state.player1.board.append(m1)
        state.player2.board.append(m2)

        engine.resolve_combat(m1, m2)
        engine.remove_dead_minions(state)
        assert len(state.player1.board) == 0
        assert len(state.player2.board) == 0

    def test_end_turn_resets_minion_attacks(self):
        engine = GameEngine()
        state = _make_game()
        m = MinionState(card_id="a", name="A", attack=2, health=3,
                        max_health=3, mana_cost=2, summoned_this_turn=False,
                        attacks_this_turn=1)
        state.current_player.board.append(m)

        engine.end_turn(state)
        # After end_turn, the minion on the NEW current player's board
        # should keep its state, but the previous player's minion resets
        prev_player = state.opponent  # previous current is now opponent
        assert prev_player.board[0].attacks_this_turn == 0
        assert prev_player.board[0].summoned_this_turn is False
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write implementation**

```python
# src/simulator/engine.py
from __future__ import annotations

import copy
import logging
import random
from typing import TYPE_CHECKING

from src.simulator.game_state import GameState, MinionState, PlayerState, HeroState

if TYPE_CHECKING:
    from src.simulator.actions import PlayCard, Attack

logger = logging.getLogger(__name__)

MAX_MANA = 10
STARTING_HAND_FIRST = 3
STARTING_HAND_SECOND = 4


class GameEngine:
    def __init__(self, card_db: dict | None = None):
        self.card_db = card_db or {}

    def start_game(self, state: GameState):
        random.shuffle(state.player1.deck)
        random.shuffle(state.player2.deck)

        for _ in range(STARTING_HAND_FIRST):
            state.player1.draw_card()
        for _ in range(STARTING_HAND_SECOND):
            state.player2.draw_card()

    def start_turn(self, state: GameState):
        player = state.current_player
        player.max_mana = min(player.max_mana + 1, MAX_MANA)
        player.mana = player.max_mana - player.overload
        player.overload = 0
        player.hero.hero_power_used = False
        player.hero.attack = 0
        player.draw_card()

    def end_turn(self, state: GameState):
        player = state.current_player
        for m in player.board:
            m.attacks_this_turn = 0
            m.summoned_this_turn = False
            if m.frozen:
                m.frozen = False

        state.switch_turn()

    def resolve_combat(self, attacker: MinionState, defender: MinionState):
        dmg_to_defender = attacker.attack
        dmg_to_attacker = defender.attack

        defender.take_damage(dmg_to_defender)
        attacker.take_damage(dmg_to_attacker)

        if attacker.lifesteal:
            # heal the attacker's hero (handled externally if needed)
            pass
        if defender.lifesteal:
            pass

        attacker.attacks_this_turn += 1

    def attack_hero(self, attacker: MinionState, hero: HeroState):
        hero.take_damage(attacker.attack)
        attacker.attacks_this_turn += 1

    def remove_dead_minions(self, state: GameState):
        state.player1.board = [m for m in state.player1.board if not m.is_dead]
        state.player2.board = [m for m in state.player2.board if not m.is_dead]

    def play_minion(self, state: GameState, card_data: dict) -> MinionState | None:
        player = state.current_player
        if player.board_full:
            return None

        mechanics = card_data.get("mechanics", [])
        minion = MinionState(
            card_id=card_data.get("card_id", ""),
            name=card_data.get("name", ""),
            attack=card_data.get("attack", 0),
            health=card_data.get("health", 1),
            max_health=card_data.get("health", 1),
            mana_cost=card_data.get("mana_cost", 0),
            taunt="TAUNT" in mechanics,
            divine_shield="DIVINE_SHIELD" in mechanics,
            stealth="STEALTH" in mechanics,
            windfury="WINDFURY" in mechanics,
            lifesteal="LIFESTEAL" in mechanics,
            poisonous="POISONOUS" in mechanics,
            reborn="REBORN" in mechanics,
            rush="RUSH" in mechanics,
            charge="CHARGE" in mechanics,
            mechanics=mechanics,
        )
        player.board.append(minion)
        player.mana -= card_data.get("mana_cost", 0)
        return minion

    def play_spell(self, state: GameState, card_data: dict, target=None):
        player = state.current_player
        player.mana -= card_data.get("mana_cost", 0)
        # Spell effects handled by effects system

    def use_hero_power(self, state: GameState, target=None):
        player = state.current_player
        if player.hero.hero_power_used or player.mana < player.hero.hero_power_cost:
            return
        player.mana -= player.hero.hero_power_cost
        player.hero.hero_power_used = True

        hero_class = player.hero.hero_class
        opponent = state.opponent

        if hero_class == "MAGE":
            if target and isinstance(target, MinionState):
                target.take_damage(1)
            elif target and isinstance(target, HeroState):
                target.take_damage(1)
            else:
                opponent.hero.take_damage(1)
        elif hero_class == "WARRIOR":
            player.hero.armor += 2
        elif hero_class == "PRIEST":
            if target and isinstance(target, MinionState):
                target.health = min(target.health + 2, target.max_health)
            else:
                player.hero.health = min(player.hero.health + 2, player.hero.max_health)
        elif hero_class == "HUNTER":
            opponent.hero.take_damage(2)
        elif hero_class == "PALADIN":
            if not player.board_full:
                token = MinionState(card_id="CS2_101t", name="Silver Hand Recruit",
                                    attack=1, health=1, max_health=1, mana_cost=0)
                player.board.append(token)
        elif hero_class == "WARLOCK":
            player.hero.take_damage(2)
            player.draw_card()
        elif hero_class == "ROGUE":
            player.hero.weapon = __import__('src.simulator.game_state', fromlist=['WeaponState']).WeaponState(
                card_id="CS2_082", name="Wicked Knife", attack=1, durability=2)
        elif hero_class == "SHAMAN":
            if not player.board_full:
                totems = [
                    MinionState(card_id="t1", name="Healing Totem", attack=0, health=2, max_health=2, mana_cost=0),
                    MinionState(card_id="t2", name="Searing Totem", attack=1, health=1, max_health=1, mana_cost=0),
                    MinionState(card_id="t3", name="Stoneclaw Totem", attack=0, health=2, max_health=2, mana_cost=0, taunt=True),
                    MinionState(card_id="t4", name="Wrath of Air Totem", attack=0, health=2, max_health=2, mana_cost=0),
                ]
                player.board.append(random.choice(totems))
        elif hero_class == "DRUID":
            player.hero.armor += 1
            player.hero.attack += 1
        elif hero_class == "DEMON_HUNTER":
            player.hero.attack += 1
        elif hero_class == "DEATH_KNIGHT":
            # Placeholder: ghoul token
            if not player.board_full:
                token = MinionState(card_id="dk_ghoul", name="Ghoul",
                                    attack=1, health=1, max_health=1, mana_cost=0)
                player.board.append(token)

    def get_legal_actions(self, state: GameState) -> list:
        from src.simulator.actions import PlayCard, Attack, HeroPower, EndTurn

        actions: list = []
        player = state.current_player
        opponent = state.opponent

        # Playable cards from hand
        for i, card_id in enumerate(player.hand):
            card_data = self.card_db.get(card_id)
            if card_data and card_data.get("mana_cost", 99) <= player.mana:
                card_type = card_data.get("card_type", "")
                if card_type == "MINION" and player.board_full:
                    continue
                actions.append(PlayCard(card_id=card_id, hand_idx=i))

        # Attacks
        has_taunt = any(m.taunt for m in opponent.board)
        for i, m in enumerate(player.board):
            if not m.can_attack:
                continue
            if m.can_attack_minions:
                for j, target in enumerate(opponent.board):
                    if has_taunt and not target.taunt:
                        continue
                    actions.append(Attack(attacker_idx=i, target_idx=j))
            if m.can_attack_hero and (not has_taunt):
                actions.append(Attack(attacker_idx=i, target_idx=-1, target_is_hero=True))

        # Hero power
        if not player.hero.hero_power_used and player.mana >= player.hero.hero_power_cost:
            actions.append(HeroPower())

        # Always can end turn
        actions.append(EndTurn())

        return actions
```

- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add game engine with turn management and combat"
```

---

### Task 4: Effect system

**Files:**
- Create: `src/simulator/effects.py`
- Create: `tests/test_effects.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_effects.py
from src.simulator.effects import EffectRegistry, EventType
from src.simulator.game_state import (
    GameState, PlayerState, HeroState, MinionState,
)


def _make_state():
    return GameState(
        player1=PlayerState(hero=HeroState(hero_class="MAGE")),
        player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
    )


class TestEffectRegistry:
    def test_register_and_trigger(self):
        registry = EffectRegistry()
        triggered = []

        def on_play(state, ctx):
            triggered.append(ctx["card_id"])

        registry.register("TEST_CARD", EventType.ON_PLAY, on_play)
        state = _make_state()
        registry.trigger(EventType.ON_PLAY, state, {"card_id": "TEST_CARD"})
        assert triggered == ["TEST_CARD"]

    def test_unregistered_card_no_effect(self):
        registry = EffectRegistry()
        state = _make_state()
        # Should not raise
        registry.trigger(EventType.ON_PLAY, state, {"card_id": "UNKNOWN"})

    def test_multiple_effects_same_event(self):
        registry = EffectRegistry()
        results = []

        registry.register("CARD_A", EventType.ON_PLAY, lambda s, c: results.append("A"))
        registry.register("CARD_B", EventType.ON_PLAY, lambda s, c: results.append("B"))

        state = _make_state()
        registry.trigger(EventType.ON_PLAY, state, {"card_id": "CARD_A"})
        registry.trigger(EventType.ON_PLAY, state, {"card_id": "CARD_B"})
        assert results == ["A", "B"]

    def test_global_event_triggers_for_all(self):
        registry = EffectRegistry()
        triggered = []

        registry.register_global(EventType.ON_TURN_START, lambda s, c: triggered.append("global"))

        state = _make_state()
        registry.trigger_global(EventType.ON_TURN_START, state, {})
        assert triggered == ["global"]
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write implementation**

```python
# src/simulator/effects.py
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
        effects = self._card_effects.get(card_id, {}).get(event, [])
        for fn in effects:
            fn(state, ctx)

    def trigger_global(self, event: EventType, state: GameState, ctx: dict):
        for fn in self._global_effects.get(event, []):
            fn(state, ctx)
```

- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add event-based effect system with EffectRegistry"
```

---

### Task 5: AI decision making

**Files:**
- Create: `src/simulator/ai.py`
- Create: `tests/test_ai.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ai.py
import pytest
from src.simulator.game_state import (
    GameState, PlayerState, HeroState, MinionState,
)
from src.simulator.ai import SimpleAI
from src.simulator.engine import GameEngine


def _make_game_with_cards(card_db):
    engine = GameEngine(card_db=card_db)
    return GameState(
        player1=PlayerState(hero=HeroState(hero_class="MAGE")),
        player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
    ), engine


class TestSimpleAI:
    def test_returns_end_turn_when_no_good_actions(self):
        ai = SimpleAI()
        state = GameState(
            player1=PlayerState(hero=HeroState(hero_class="MAGE"), mana=0),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        engine = GameEngine()
        action = ai.choose_action(state, engine)
        from src.simulator.actions import EndTurn
        assert isinstance(action, EndTurn)

    def test_plays_affordable_minion(self):
        card_db = {
            "yeti": {"card_id": "yeti", "card_type": "MINION", "mana_cost": 4,
                     "attack": 4, "health": 5, "mechanics": []},
        }
        ai = SimpleAI()
        state = GameState(
            player1=PlayerState(hero=HeroState(hero_class="MAGE"), mana=4,
                                max_mana=4, hand=["yeti"]),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        engine = GameEngine(card_db=card_db)
        action = ai.choose_action(state, engine)
        from src.simulator.actions import PlayCard
        assert isinstance(action, PlayCard)

    def test_attacks_when_possible(self):
        ai = SimpleAI()
        state = GameState(
            player1=PlayerState(
                hero=HeroState(hero_class="MAGE"), mana=0,
                board=[MinionState(card_id="a", name="A", attack=3, health=2,
                                   max_health=2, mana_cost=2, summoned_this_turn=False)],
            ),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        engine = GameEngine()
        action = ai.choose_action(state, engine)
        from src.simulator.actions import Attack
        assert isinstance(action, Attack)

    def test_mulligan_keeps_low_cost(self):
        ai = SimpleAI()
        card_db = {
            "cheap": {"mana_cost": 2},
            "expensive": {"mana_cost": 7},
            "mid": {"mana_cost": 4},
        }
        hand = ["cheap", "expensive", "mid"]
        keep = ai.mulligan(hand, card_db)
        assert "cheap" in keep
        assert "expensive" not in keep
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write implementation**

```python
# src/simulator/ai.py
from __future__ import annotations

import random
from typing import TYPE_CHECKING

from src.simulator.actions import PlayCard, Attack, HeroPower, EndTurn

if TYPE_CHECKING:
    from src.simulator.engine import GameEngine
    from src.simulator.game_state import GameState

MULLIGAN_COST_THRESHOLD = 3


class SimpleAI:
    """Rule-based heuristic AI for game simulation."""

    def choose_action(self, state: GameState, engine: GameEngine):
        actions = engine.get_legal_actions(state)

        # Priority 1: favorable attacks
        attacks = [a for a in actions if isinstance(a, Attack)]
        if attacks:
            return self._best_attack(attacks, state)

        # Priority 2: play cards (highest mana cost first for efficiency)
        plays = [a for a in actions if isinstance(a, PlayCard)]
        if plays:
            plays.sort(key=lambda p: engine.card_db.get(p.card_id, {}).get("mana_cost", 0), reverse=True)
            return plays[0]

        # Priority 3: hero power
        hero_powers = [a for a in actions if isinstance(a, HeroPower)]
        if hero_powers:
            return hero_powers[0]

        return EndTurn()

    def _best_attack(self, attacks: list[Attack], state: GameState) -> Attack:
        player = state.current_player
        opponent = state.opponent

        # Prefer killing taunts first, then favorable trades, then face
        best = None
        best_score = -999

        for a in attacks:
            if a.target_is_hero:
                score = player.board[a.attacker_idx].attack  # face damage value
            else:
                attacker = player.board[a.attacker_idx]
                defender = opponent.board[a.target_idx]
                if defender.health <= attacker.attack:
                    score = defender.mana_cost + 10  # bonus for killing
                    if defender.taunt:
                        score += 20  # high priority to remove taunt
                else:
                    score = 0  # unfavorable trade

            if score > best_score:
                best_score = score
                best = a

        return best or attacks[0]

    def mulligan(self, hand: list[str], card_db: dict) -> list[str]:
        keep = []
        for card_id in hand:
            cost = card_db.get(card_id, {}).get("mana_cost", 99)
            if cost <= MULLIGAN_COST_THRESHOLD:
                keep.append(card_id)
        return keep
```

- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add rule-based AI with heuristic decision making"
```

---

### Task 6: Match runner

**Files:**
- Create: `src/simulator/match.py`
- Create: `tests/test_match.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_match.py
import pytest
from src.simulator.match import run_match, MatchResult


CARD_DB = {
    f"card_{i}": {
        "card_id": f"card_{i}",
        "card_type": "MINION",
        "mana_cost": (i % 8) + 1,
        "attack": (i % 5) + 1,
        "health": (i % 5) + 1,
        "mechanics": [],
        "name": f"Card {i}",
    }
    for i in range(30)
}


class TestRunMatch:
    def test_match_completes(self):
        deck_a = [f"card_{i}" for i in range(15)] * 2
        deck_b = [f"card_{i}" for i in range(15)] * 2
        result = run_match(
            deck_a=deck_a, deck_b=deck_b,
            hero_a="MAGE", hero_b="WARRIOR",
            card_db=CARD_DB, max_turns=45,
        )
        assert isinstance(result, MatchResult)
        assert result.turns > 0
        assert result.turns <= 45

    def test_match_has_winner_or_draw(self):
        deck_a = [f"card_{i}" for i in range(15)] * 2
        deck_b = [f"card_{i}" for i in range(15)] * 2
        result = run_match(
            deck_a=deck_a, deck_b=deck_b,
            hero_a="MAGE", hero_b="WARRIOR",
            card_db=CARD_DB, max_turns=45,
        )
        assert result.winner in ("A", "B", None)

    def test_match_respects_max_turns(self):
        # With very few cards, game should end quickly by fatigue or max turns
        deck_a = ["card_0"] * 2
        deck_b = ["card_0"] * 2
        result = run_match(
            deck_a=deck_a, deck_b=deck_b,
            hero_a="MAGE", hero_b="WARRIOR",
            card_db=CARD_DB, max_turns=10,
        )
        assert result.turns <= 10
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write implementation**

```python
# src/simulator/match.py
from __future__ import annotations

import copy
import logging
from dataclasses import dataclass

from src.simulator.ai import SimpleAI
from src.simulator.engine import GameEngine
from src.simulator.game_state import GameState, PlayerState, HeroState
from src.simulator.actions import PlayCard, Attack, HeroPower, EndTurn

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    winner: str | None  # "A", "B", or None (draw)
    turns: int


def run_match(
    deck_a: list[str],
    deck_b: list[str],
    hero_a: str,
    hero_b: str,
    card_db: dict,
    max_turns: int = 45,
) -> MatchResult:
    engine = GameEngine(card_db=card_db)
    ai = SimpleAI()

    state = GameState(
        player1=PlayerState(hero=HeroState(hero_class=hero_a), deck=list(deck_a)),
        player2=PlayerState(hero=HeroState(hero_class=hero_b), deck=list(deck_b)),
    )

    # Mulligan
    engine.start_game(state)

    keep_1 = ai.mulligan(state.player1.hand, card_db)
    _do_mulligan(state.player1, keep_1, card_db)

    keep_2 = ai.mulligan(state.player2.hand, card_db)
    _do_mulligan(state.player2, keep_2, card_db)

    turn_count = 0

    while not state.game_over and turn_count < max_turns:
        engine.start_turn(state)
        turn_count += 1

        # AI takes actions until EndTurn
        action_count = 0
        while action_count < 50:  # safety limit
            action = ai.choose_action(state, engine)

            if isinstance(action, EndTurn):
                break

            _execute_action(engine, state, action, card_db)

            engine.remove_dead_minions(state)

            if state.game_over:
                break

            action_count += 1

        if state.game_over:
            break

        engine.end_turn(state)

    winner = None
    if state.game_over:
        if state.winner_idx == 0:
            winner = "A"
        elif state.winner_idx == 1:
            winner = "B"

    return MatchResult(winner=winner, turns=turn_count)


def _do_mulligan(player: PlayerState, keep: list[str], card_db: dict):
    new_hand = []
    returned = []
    for card_id in player.hand:
        if card_id in keep:
            new_hand.append(card_id)
            keep.remove(card_id)  # remove first match only
        else:
            returned.append(card_id)

    player.hand = new_hand
    player.deck.extend(returned)
    import random
    random.shuffle(player.deck)

    for _ in range(len(returned)):
        player.draw_card()


def _execute_action(engine: GameEngine, state: GameState, action, card_db: dict):
    if isinstance(action, PlayCard):
        player = state.current_player
        if action.hand_idx < len(player.hand):
            card_id = player.hand.pop(action.hand_idx)
            card_data = card_db.get(card_id, {})
            card_type = card_data.get("card_type", "MINION")
            if card_type == "MINION":
                engine.play_minion(state, card_data)
            elif card_type == "SPELL":
                engine.play_spell(state, card_data)
            elif card_type == "WEAPON":
                from src.simulator.game_state import WeaponState
                player.hero.weapon = WeaponState(
                    card_id=card_data.get("card_id", ""),
                    name=card_data.get("name", ""),
                    attack=card_data.get("attack", 0),
                    durability=card_data.get("durability", 1),
                )
                player.mana -= card_data.get("mana_cost", 0)

    elif isinstance(action, Attack):
        player = state.current_player
        opponent = state.opponent
        if action.attacker_idx < len(player.board):
            attacker = player.board[action.attacker_idx]
            if action.target_is_hero:
                engine.attack_hero(attacker, opponent.hero)
            elif action.target_idx < len(opponent.board):
                engine.resolve_combat(attacker, opponent.board[action.target_idx])

    elif isinstance(action, HeroPower):
        engine.use_hero_power(state)
```

- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add match runner with AI-driven game simulation"
```

---

### Task 7: Wire CLI simulate command and full test

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update main.py simulate command**

Wire the simulate command to run a single match or bulk matches. For now, just a demo run.

- [ ] **Step 2: Run full test suite**

Run: `.venv/Scripts/python -m pytest tests/ -v --tb=short`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: wire simulate CLI command to match runner"
```
