# Sub-Project 1: Project Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up the complete project structure, database schema, configuration, core models, and development tooling for the Hearthstone Deck Maker project.

**Architecture:** Monolithic Python project with modular directory structure. SQLAlchemy ORM with Alembic migrations, SQLite default with PostgreSQL readiness. Pydantic models for validation, enums for type safety.

**Tech Stack:** Python 3.11+, SQLAlchemy 2.0, Alembic, Pydantic v2, pytest, FastAPI (shell only)

**Spec:** `docs/superpowers/specs/2026-03-24-hearthstone-deckmaker-design.md`

---

## File Structure

```
hearthstone_deckmaker/
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── enums.py          # CardType, Rarity, HeroClass, GameFormat, Archetype, MechanicType
│   │   ├── models.py         # Pydantic models: CardData, DeckData (PlayerState/GameState deferred to sub-project 3)
│   │   ├── rules.py          # Deck validation: 30 cards, legendary limit, class cards, format
│   │   └── deckstring.py     # Stub for deckstring encode/decode (implemented in sub-project 4)
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py       # SQLAlchemy engine, session factory, get_db()
│   │   └── tables.py         # ORM models: Card, Deck, DeckCard, Simulation, HSReplayStats, TierHistory
│   ├── collector/
│   │   └── __init__.py
│   ├── simulator/
│   │   └── __init__.py
│   ├── deckbuilder/
│   │   └── __init__.py
│   ├── scraper/
│   │   └── __init__.py
│   ├── tierlist/
│   │   └── __init__.py
│   ├── web/
│   │   ├── __init__.py
│   │   └── static/
│   │       └── card_cache/
│   │           └── .gitkeep
│   └── scheduler/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # pytest fixtures: in-memory DB session, sample card/deck data
│   ├── test_enums.py
│   ├── test_models.py
│   ├── test_rules.py
│   └── test_tables.py
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── .gitkeep
├── alembic.ini
├── pyproject.toml            # pytest config (pythonpath) + project metadata
├── config.py                 # All configuration constants
├── requirements.txt
├── requirements-dev.txt
├── main.py                   # CLI entry point (placeholder)
├── .gitignore
└── .env.example
```

---

### Task 1: Project scaffolding and dependencies

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `src/__init__.py` and all module `__init__.py` files
- Create: `src/web/static/card_cache/.gitkeep`
- Create: `tests/__init__.py`

- [ ] **Step 0: Create pyproject.toml**

```toml
[project]
name = "hearthstone-deckmaker"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 1: Create requirements.txt**

```
sqlalchemy>=2.0,<3.0
alembic>=1.13,<2.0
pydantic>=2.0,<3.0
pydantic-settings>=2.0,<3.0
fastapi>=0.110,<1.0
uvicorn[standard]>=0.27,<1.0
jinja2>=3.1,<4.0
httpx>=0.27,<1.0
playwright>=1.41,<2.0
apscheduler>=3.10,<4.0
pillow>=10.0,<11.0
python-dotenv>=1.0,<2.0
```

- [ ] **Step 2: Create requirements-dev.txt**

```
-r requirements.txt
pytest>=8.0,<9.0
pytest-asyncio>=0.23,<1.0
pytest-cov>=4.0,<6.0
```

- [ ] **Step 3: Create .gitignore**

```
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/
*.egg
.env
*.db
*.sqlite3
src/web/static/card_cache/*.png
src/web/static/card_cache/*.jpg
.venv/
venv/
.pytest_cache/
.coverage
htmlcov/
```

- [ ] **Step 4: Create .env.example**

```
DATABASE_URL=sqlite:///hearthstone.db
BLIZZARD_CLIENT_ID=
BLIZZARD_CLIENT_SECRET=
```

- [ ] **Step 5: Create all __init__.py files and .gitkeep**

Create empty `__init__.py` in:
- `src/`
- `src/core/`
- `src/db/`
- `src/collector/`
- `src/simulator/`
- `src/deckbuilder/`
- `src/scraper/`
- `src/tierlist/`
- `src/web/`
- `src/scheduler/`
- `tests/`

Create empty `.gitkeep` in:
- `src/web/static/card_cache/`

Create stub `src/core/deckstring.py`:
```python
# src/core/deckstring.py
"""Deckstring encode/decode - implemented in sub-project 4."""
```

- [ ] **Step 6: Install dependencies and verify**

Run: `python -m venv .venv && .venv/Scripts/activate && pip install -r requirements-dev.txt`
Expected: All packages install successfully

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: scaffold project structure with dependencies"
```

---

### Task 2: Configuration module

**Files:**
- Create: `config.py`

- [ ] **Step 1: Create config.py**

```python
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///hearthstone.db"

    # Blizzard API
    BLIZZARD_CLIENT_ID: str = ""
    BLIZZARD_CLIENT_SECRET: str = ""
    BLIZZARD_API_REGION: str = "kr"

    # HearthstoneJSON
    HEARTHSTONE_JSON_URL: str = "https://api.hearthstonejson.com/v1/latest"

    # Image Cache
    BASE_DIR: Path = Path(__file__).parent
    IMAGE_CACHE_DIR: Path = BASE_DIR / "src" / "web" / "static" / "card_cache"
    IMAGE_BASE_URL: str = "https://art.hearthstonejson.com/v1/render/latest/koKR/512x"

    # Simulation
    SIM_MATCHES_PER_MATCHUP: int = 100
    SIM_MAX_TURNS: int = 45
    MCTS_ITERATIONS: int = 1000
    MCTS_ITERATIONS_BULK: int = 200

    # Tier List
    TIER_WEIGHT_SIM: float = 0.5
    TIER_WEIGHT_HSREPLAY: float = 0.5
    TIER_THRESHOLDS: dict = {"S": 55.0, "A": 52.0, "B": 49.0, "C": 46.0}
    TIER_MIN_GAMES: int = 50

    # Scheduler
    SCHEDULER_CRON_HOUR: int = 3
    SCHEDULER_CRON_MINUTE: int = 0

    # Web
    WEB_HOST: str = "127.0.0.1"
    WEB_PORT: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 2: Verify config loads**

Run: `python -c "from config import settings; print(settings.DATABASE_URL)"`
Expected: `sqlite:///hearthstone.db`

- [ ] **Step 3: Commit**

```bash
git add config.py
git commit -m "feat: add configuration module with pydantic-settings"
```

---

### Task 3: Core enums

**Files:**
- Create: `src/core/enums.py`
- Create: `tests/test_enums.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_enums.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_enums.py -v`
Expected: FAIL - ImportError

- [ ] **Step 3: Write implementation**

```python
# src/core/enums.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_enums.py -v`
Expected: All PASSED

- [ ] **Step 5: Commit**

```bash
git add src/core/enums.py tests/test_enums.py
git commit -m "feat: add core enums for card types, rarity, classes, mechanics"
```

---

### Task 4: Core Pydantic models

**Files:**
- Create: `src/core/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
import pytest
from src.core.enums import CardType, Rarity, HeroClass, GameFormat, Archetype
from src.core.models import CardData, DeckData


class TestCardData:
    def test_create_minion(self):
        card = CardData(
            card_id="CS2_182",
            dbf_id=1369,
            name="Chillwind Yeti",
            name_ko="칠풍의 예티",
            card_type=CardType.MINION,
            hero_class=HeroClass.NEUTRAL,
            mana_cost=4,
            attack=4,
            health=5,
            rarity=Rarity.FREE,
            set_name="CORE",
            collectible=True,
            is_standard=True,
        )
        assert card.card_id == "CS2_182"
        assert card.attack == 4
        assert card.health == 5

    def test_create_spell(self):
        card = CardData(
            card_id="CS2_029",
            dbf_id=522,
            name="Fireball",
            name_ko="화염구",
            card_type=CardType.SPELL,
            hero_class=HeroClass.MAGE,
            mana_cost=4,
            rarity=Rarity.FREE,
            set_name="CORE",
            collectible=True,
            is_standard=True,
        )
        assert card.attack is None
        assert card.health is None

    def test_create_weapon(self):
        card = CardData(
            card_id="CS2_106",
            dbf_id=401,
            name="Fiery War Axe",
            name_ko="불타는 전쟁도끼",
            card_type=CardType.WEAPON,
            hero_class=HeroClass.WARRIOR,
            mana_cost=3,
            attack=3,
            durability=2,
            rarity=Rarity.FREE,
            set_name="CORE",
            collectible=True,
            is_standard=True,
        )
        assert card.durability == 2

    def test_mechanics_default_empty(self):
        card = CardData(
            card_id="CS2_182",
            dbf_id=1369,
            name="Chillwind Yeti",
            name_ko="칠풍의 예티",
            card_type=CardType.MINION,
            hero_class=HeroClass.NEUTRAL,
            mana_cost=4,
            attack=4,
            health=5,
            rarity=Rarity.FREE,
            set_name="CORE",
            collectible=True,
            is_standard=True,
        )
        assert card.mechanics == []

    def test_negative_mana_cost_rejected(self):
        with pytest.raises(ValueError):
            CardData(
                card_id="BAD",
                dbf_id=1,
                name="Bad",
                name_ko="나쁨",
                card_type=CardType.MINION,
                hero_class=HeroClass.NEUTRAL,
                mana_cost=-1,
                rarity=Rarity.FREE,
                set_name="CORE",
                collectible=True,
                is_standard=True,
            )


class TestDeckData:
    def test_create_deck(self):
        deck = DeckData(
            name="Test Deck",
            hero_class=HeroClass.MAGE,
            format=GameFormat.STANDARD,
            cards={"CS2_029": 2, "CS2_182": 2},
            source="manual",
        )
        assert deck.name == "Test Deck"
        assert deck.hero_class == HeroClass.MAGE
        assert deck.total_cards == 4

    def test_archetype_default_none(self):
        deck = DeckData(
            name="Test",
            hero_class=HeroClass.MAGE,
            format=GameFormat.STANDARD,
            cards={},
            source="manual",
        )
        assert deck.archetype is None

    def test_deckstring_optional(self):
        deck = DeckData(
            name="Test",
            hero_class=HeroClass.MAGE,
            format=GameFormat.STANDARD,
            cards={},
            source="manual",
        )
        assert deck.deckstring is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL - ImportError

- [ ] **Step 3: Write implementation**

```python
# src/core/models.py
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from src.core.enums import (
    Archetype,
    CardType,
    GameFormat,
    HeroClass,
    Rarity,
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_models.py -v`
Expected: All PASSED

- [ ] **Step 5: Commit**

```bash
git add src/core/models.py tests/test_models.py
git commit -m "feat: add Pydantic card and deck data models"
```

---

### Task 5: Deck validation rules

**Files:**
- Create: `src/core/rules.py`
- Create: `tests/test_rules.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rules.py
import pytest
from src.core.enums import (
    CardType, Rarity, HeroClass, GameFormat,
)
from src.core.models import CardData, DeckData
from src.core.rules import validate_deck, DeckValidationError


def _card(card_id: str, hero_class: HeroClass = HeroClass.NEUTRAL,
          rarity: Rarity = Rarity.COMMON, is_standard: bool = True) -> CardData:
    return CardData(
        card_id=card_id, dbf_id=hash(card_id) % 10000, name=card_id,
        name_ko=card_id, card_type=CardType.MINION, hero_class=hero_class,
        mana_cost=1, attack=1, health=1, rarity=rarity, set_name="TEST",
        collectible=True, is_standard=is_standard,
    )


def _card_db(cards: list[CardData]) -> dict[str, CardData]:
    return {c.card_id: c for c in cards}


class TestValidateDeck:
    def test_valid_30_card_deck(self):
        cards = [_card(f"card_{i}") for i in range(15)]
        card_db = _card_db(cards)
        deck = DeckData(
            name="Valid", hero_class=HeroClass.MAGE,
            format=GameFormat.STANDARD,
            cards={f"card_{i}": 2 for i in range(15)},
            source="manual",
        )
        errors = validate_deck(deck, card_db)
        assert errors == []

    def test_too_many_cards(self):
        cards = [_card(f"card_{i}") for i in range(16)]
        card_db = _card_db(cards)
        deck = DeckData(
            name="Too Many", hero_class=HeroClass.MAGE,
            format=GameFormat.STANDARD,
            cards={f"card_{i}": 2 for i in range(16)},
            source="manual",
        )
        errors = validate_deck(deck, card_db)
        assert any("30" in str(e) for e in errors)

    def test_too_few_cards(self):
        cards = [_card("card_0")]
        card_db = _card_db(cards)
        deck = DeckData(
            name="Too Few", hero_class=HeroClass.MAGE,
            format=GameFormat.STANDARD,
            cards={"card_0": 1},
            source="manual",
        )
        errors = validate_deck(deck, card_db)
        assert any("30" in str(e) for e in errors)

    def test_legendary_max_one_copy(self):
        cards = [_card("legend_1", rarity=Rarity.LEGENDARY)]
        cards += [_card(f"card_{i}") for i in range(14)]
        card_db = _card_db(cards)
        deck = DeckData(
            name="Bad Legendary", hero_class=HeroClass.MAGE,
            format=GameFormat.STANDARD,
            cards={"legend_1": 2, **{f"card_{i}": 2 for i in range(14)}},
            source="manual",
        )
        errors = validate_deck(deck, card_db)
        assert any("legendary" in str(e).lower() for e in errors)

    def test_wrong_class_card(self):
        warrior_card = _card("warrior_1", hero_class=HeroClass.WARRIOR)
        cards = [warrior_card] + [_card(f"card_{i}") for i in range(14)]
        card_db = _card_db(cards)
        deck = DeckData(
            name="Wrong Class", hero_class=HeroClass.MAGE,
            format=GameFormat.STANDARD,
            cards={"warrior_1": 2, **{f"card_{i}": 2 for i in range(14)}},
            source="manual",
        )
        errors = validate_deck(deck, card_db)
        assert any("class" in str(e).lower() for e in errors)

    def test_wild_card_in_standard_deck(self):
        wild_only = _card("wild_1", is_standard=False)
        cards = [wild_only] + [_card(f"card_{i}") for i in range(14)]
        card_db = _card_db(cards)
        deck = DeckData(
            name="Wild in Standard", hero_class=HeroClass.MAGE,
            format=GameFormat.STANDARD,
            cards={"wild_1": 2, **{f"card_{i}": 2 for i in range(14)}},
            source="manual",
        )
        errors = validate_deck(deck, card_db)
        assert any("standard" in str(e).lower() for e in errors)

    def test_wild_format_allows_all(self):
        wild_only = _card("wild_1", is_standard=False)
        cards = [wild_only] + [_card(f"card_{i}") for i in range(14)]
        card_db = _card_db(cards)
        deck = DeckData(
            name="Wild OK", hero_class=HeroClass.MAGE,
            format=GameFormat.WILD,
            cards={"wild_1": 2, **{f"card_{i}": 2 for i in range(14)}},
            source="manual",
        )
        errors = validate_deck(deck, card_db)
        assert errors == []

    def test_unknown_card_rejected(self):
        deck = DeckData(
            name="Unknown", hero_class=HeroClass.MAGE,
            format=GameFormat.STANDARD,
            cards={"nonexistent": 2},
            source="manual",
        )
        errors = validate_deck(deck, {})
        assert any("not found" in str(e).lower() for e in errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_rules.py -v`
Expected: FAIL - ImportError

- [ ] **Step 3: Write implementation**

```python
# src/core/rules.py
from __future__ import annotations

from dataclasses import dataclass

from src.core.enums import GameFormat, HeroClass, Rarity
from src.core.models import CardData, DeckData

DECK_SIZE = 30
MAX_COPIES_NORMAL = 2
MAX_COPIES_LEGENDARY = 1


@dataclass
class DeckValidationError:
    message: str

    def __str__(self) -> str:
        return self.message


def validate_deck(deck: DeckData, card_db: dict[str, CardData]) -> list[DeckValidationError]:
    errors: list[DeckValidationError] = []

    # Check total card count
    total = deck.total_cards
    if total != DECK_SIZE:
        errors.append(DeckValidationError(
            message=f"Deck must have exactly {DECK_SIZE} cards, got {total}"
        ))

    for card_id, count in deck.cards.items():
        # Check card exists
        card = card_db.get(card_id)
        if card is None:
            errors.append(DeckValidationError(
                message=f"Card not found: {card_id}"
            ))
            continue

        # Check copy limit
        max_copies = MAX_COPIES_LEGENDARY if card.rarity == Rarity.LEGENDARY else MAX_COPIES_NORMAL
        if count > max_copies:
            errors.append(DeckValidationError(
                message=f"Legendary card '{card.name}' can only have {MAX_COPIES_LEGENDARY} copy"
            ))

        # Check class restriction
        if card.hero_class not in (HeroClass.NEUTRAL, deck.hero_class):
            errors.append(DeckValidationError(
                message=f"Card '{card.name}' is {card.hero_class.value} class, "
                f"not allowed in {deck.hero_class.value} deck"
            ))

        # Check format restriction
        if deck.format == GameFormat.STANDARD and not card.is_standard:
            errors.append(DeckValidationError(
                message=f"Card '{card.name}' is not in Standard format"
            ))

    return errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_rules.py -v`
Expected: All PASSED

- [ ] **Step 5: Commit**

```bash
git add src/core/rules.py tests/test_rules.py
git commit -m "feat: add deck validation rules (30 cards, legendary, class, format)"
```

---

### Task 6: Database setup and ORM tables

**Files:**
- Create: `src/db/database.py`
- Create: `src/db/tables.py`
- Create: `tests/conftest.py`
- Create: `tests/test_tables.py`

- [ ] **Step 1: Write conftest.py with DB fixtures**

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.tables import Base


@pytest.fixture
def db_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    with Session(db_engine) as session:
        yield session
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_tables.py
from datetime import datetime, timezone

from src.db.tables import Card, Deck, DeckCard, Simulation, HSReplayStats, TierHistory


class TestCardTable:
    def test_create_card(self, db_session):
        card = Card(
            card_id="CS2_182", dbf_id=1369, name="Chillwind Yeti",
            name_ko="칠풍의 예티", card_type="MINION", hero_class="NEUTRAL",
            mana_cost=4, attack=4, health=5, rarity="FREE", set_name="CORE",
            collectible=True, is_standard=True,
        )
        db_session.add(card)
        db_session.commit()

        result = db_session.query(Card).filter_by(card_id="CS2_182").one()
        assert result.name == "Chillwind Yeti"
        assert result.attack == 4

    def test_card_id_unique(self, db_session):
        card1 = Card(card_id="CS2_182", dbf_id=1369, name="A",
                     name_ko="A", card_type="MINION", hero_class="NEUTRAL",
                     mana_cost=1, rarity="FREE", set_name="CORE",
                     collectible=True, is_standard=True)
        card2 = Card(card_id="CS2_182", dbf_id=9999, name="B",
                     name_ko="B", card_type="MINION", hero_class="NEUTRAL",
                     mana_cost=1, rarity="FREE", set_name="CORE",
                     collectible=True, is_standard=True)
        db_session.add(card1)
        db_session.commit()
        db_session.add(card2)
        import sqlalchemy
        with __import__("pytest").raises(sqlalchemy.exc.IntegrityError):
            db_session.commit()


class TestDeckTable:
    def test_create_deck(self, db_session):
        deck = Deck(
            hero_class="MAGE", name="Test Deck", archetype="aggro",
            format="standard", deckstring="AAE...", source="manual",
        )
        db_session.add(deck)
        db_session.commit()
        assert deck.id is not None
        assert deck.created_at is not None


class TestDeckCardTable:
    def test_deck_card_relationship(self, db_session):
        card = Card(card_id="CS2_182", dbf_id=1369, name="Yeti",
                    name_ko="예티", card_type="MINION", hero_class="NEUTRAL",
                    mana_cost=4, attack=4, health=5, rarity="FREE",
                    set_name="CORE", collectible=True, is_standard=True)
        deck = Deck(hero_class="MAGE", name="Test", format="standard",
                    source="manual")
        db_session.add_all([card, deck])
        db_session.commit()

        dc = DeckCard(deck_id=deck.id, card_id=card.id, count=2)
        db_session.add(dc)
        db_session.commit()
        assert dc.count == 2


class TestSimulationTable:
    def test_create_simulation_with_winner(self, db_session):
        d1 = Deck(hero_class="MAGE", name="D1", format="standard", source="manual")
        d2 = Deck(hero_class="WARRIOR", name="D2", format="standard", source="manual")
        db_session.add_all([d1, d2])
        db_session.commit()

        sim = Simulation(deck_a_id=d1.id, deck_b_id=d2.id,
                         winner_id=d1.id, turns=12)
        db_session.add(sim)
        db_session.commit()
        assert sim.winner_id == d1.id

    def test_create_simulation_draw(self, db_session):
        d1 = Deck(hero_class="MAGE", name="D1", format="standard", source="manual")
        d2 = Deck(hero_class="WARRIOR", name="D2", format="standard", source="manual")
        db_session.add_all([d1, d2])
        db_session.commit()

        sim = Simulation(deck_a_id=d1.id, deck_b_id=d2.id,
                         winner_id=None, turns=45)
        db_session.add(sim)
        db_session.commit()
        assert sim.winner_id is None


class TestHSReplayStatsTable:
    def test_create_stats(self, db_session):
        deck = Deck(hero_class="MAGE", name="D1", format="standard", source="hsreplay")
        db_session.add(deck)
        db_session.commit()

        stats = HSReplayStats(deck_id=deck.id, winrate=55.3,
                              playrate=8.2, games_played=12000)
        db_session.add(stats)
        db_session.commit()
        assert stats.winrate == 55.3


class TestTierHistoryTable:
    def test_create_tier_record(self, db_session):
        deck = Deck(hero_class="MAGE", name="D1", format="standard", source="manual")
        db_session.add(deck)
        db_session.commit()

        th = TierHistory(deck_id=deck.id, tier="S", sim_winrate=56.0,
                         hsreplay_winrate=54.5, combined_winrate=55.25)
        db_session.add(th)
        db_session.commit()
        assert th.tier == "S"
        assert th.recorded_at is not None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_tables.py -v`
Expected: FAIL - ImportError

- [ ] **Step 4: Write database.py**

```python
# src/db/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,
)

SessionLocal = sessionmaker(bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: Write tables.py**

```python
# src/db/tables.py
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey,
    Index, Integer, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    card_id = Column(String, unique=True, nullable=False, index=True)
    dbf_id = Column(Integer, unique=True, nullable=False)
    name = Column(String, nullable=False)
    name_ko = Column(String, nullable=False)
    card_type = Column(String, nullable=False)
    hero_class = Column(String, nullable=False)
    mana_cost = Column(Integer, nullable=False)
    attack = Column(Integer, nullable=True)
    health = Column(Integer, nullable=True)
    durability = Column(Integer, nullable=True)
    text = Column(Text, default="")
    rarity = Column(String, nullable=False)
    set_name = Column(String, nullable=False)
    mechanics = Column(JSON, default=list)
    collectible = Column(Boolean, default=True)
    is_standard = Column(Boolean, default=False)
    json_data = Column(JSON, nullable=True)
    image_url = Column(String, default="")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_cards_class_cost", "hero_class", "mana_cost"),
    )


class Deck(Base):
    __tablename__ = "decks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hero_class = Column(String, nullable=False)
    name = Column(String, nullable=False)
    archetype = Column(String, nullable=True)
    format = Column(String, nullable=False)
    deckstring = Column(String, nullable=True)
    source = Column(String, nullable=False, default="manual")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    cards = relationship("DeckCard", back_populates="deck")


class DeckCard(Base):
    __tablename__ = "deck_cards"

    deck_id = Column(Integer, ForeignKey("decks.id"), primary_key=True)
    card_id = Column(Integer, ForeignKey("cards.id"), primary_key=True)
    count = Column(Integer, nullable=False)

    deck = relationship("Deck", back_populates="cards")
    card = relationship("Card")

    __table_args__ = (
        CheckConstraint("count >= 1 AND count <= 2", name="ck_deck_cards_count"),
        Index("ix_deck_cards_card_id", "card_id"),
    )


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deck_a_id = Column(Integer, ForeignKey("decks.id"), nullable=False)
    deck_b_id = Column(Integer, ForeignKey("decks.id"), nullable=False)
    winner_id = Column(Integer, ForeignKey("decks.id"), nullable=True)
    turns = Column(Integer, nullable=False)
    played_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    deck_a = relationship("Deck", foreign_keys=[deck_a_id])
    deck_b = relationship("Deck", foreign_keys=[deck_b_id])
    winner = relationship("Deck", foreign_keys=[winner_id])

    __table_args__ = (
        Index("ix_simulations_deck_a", "deck_a_id"),
        Index("ix_simulations_deck_b", "deck_b_id"),
    )


class HSReplayStats(Base):
    __tablename__ = "hsreplay_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deck_id = Column(Integer, ForeignKey("decks.id"), nullable=False)
    winrate = Column(Float, nullable=False)
    playrate = Column(Float, nullable=False)
    games_played = Column(Integer, nullable=False)
    collected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    deck = relationship("Deck")

    __table_args__ = (
        Index("ix_hsreplay_stats_deck_date", "deck_id", "collected_at"),
    )


class TierHistory(Base):
    __tablename__ = "tier_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deck_id = Column(Integer, ForeignKey("decks.id"), nullable=False)
    tier = Column(String, nullable=False)
    sim_winrate = Column(Float, nullable=True)
    hsreplay_winrate = Column(Float, nullable=True)
    combined_winrate = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    deck = relationship("Deck")

    __table_args__ = (
        Index("ix_tier_history_deck_date", "deck_id", "recorded_at"),
    )
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_tables.py -v`
Expected: All PASSED

- [ ] **Step 7: Commit**

```bash
git add src/db/database.py src/db/tables.py tests/conftest.py tests/test_tables.py
git commit -m "feat: add SQLAlchemy ORM tables with indexes and constraints"
```

---

### Task 7: Alembic migration setup

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/.gitkeep`

- [ ] **Step 1: Initialize Alembic**

Run: `cd C:/Users/user/OneDrive/Documents/hearthstone_deckmaker && .venv/Scripts/python -m alembic init alembic`
Expected: Alembic directory and alembic.ini created

- [ ] **Step 2: Edit alembic.ini to use config**

In `alembic.ini`, set:
```ini
sqlalchemy.url = sqlite:///hearthstone.db
```

- [ ] **Step 3: Edit alembic/env.py to import models**

Replace the `target_metadata` line in `alembic/env.py`:

```python
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.tables import Base
target_metadata = Base.metadata
```

- [ ] **Step 4: Generate initial migration**

Run: `.venv/Scripts/python -m alembic revision --autogenerate -m "initial schema"`
Expected: Migration file created in `alembic/versions/`

- [ ] **Step 5: Apply migration**

Run: `.venv/Scripts/python -m alembic upgrade head`
Expected: All tables created, `hearthstone.db` file appears

- [ ] **Step 6: Verify tables exist**

Run: `python -c "import sqlite3; conn = sqlite3.connect('hearthstone.db'); print([t[0] for t in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()])"`
Expected: List containing `cards`, `decks`, `deck_cards`, `simulations`, `hsreplay_stats`, `tier_history`

- [ ] **Step 7: Commit**

```bash
git add alembic/ alembic.ini
git commit -m "feat: add Alembic migrations with initial schema"
```

---

### Task 8: CLI entry point (placeholder)

**Files:**
- Create: `main.py`

- [ ] **Step 1: Create main.py**

```python
# main.py
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="Hearthstone Deck Maker")
    subparsers = parser.add_subparsers(dest="command")

    # Web server
    subparsers.add_parser("serve", help="Start web dashboard")

    # Card sync
    sync_parser = subparsers.add_parser("sync-cards", help="Sync card data")
    sync_parser.add_argument("--update-standard", action="store_true",
                             help="Update standard format flags")

    # Simulation
    sim_parser = subparsers.add_parser("simulate", help="Run simulations")
    sim_parser.add_argument("--bulk", action="store_true",
                            help="Run bulk simulation for all meta decks")

    # Tier list
    subparsers.add_parser("update-tierlist", help="Recalculate tier list")

    # Scheduler
    subparsers.add_parser("scheduler", help="Start daily scheduler")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "serve":
        print("Web server not yet implemented (sub-project 6)")
    elif args.command == "sync-cards":
        print("Card sync not yet implemented (sub-project 2)")
    elif args.command == "simulate":
        print("Simulation not yet implemented (sub-project 3)")
    elif args.command == "update-tierlist":
        print("Tier list not yet implemented (sub-project 5)")
    elif args.command == "scheduler":
        print("Scheduler not yet implemented (sub-project 6)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify CLI works**

Run: `python main.py --help`
Expected: Help output showing all subcommands

Run: `python main.py serve`
Expected: "Web server not yet implemented (sub-project 6)"

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add CLI entry point with placeholder subcommands"
```

---

### Task 9: Run full test suite and verify

- [ ] **Step 1: Run all tests**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All tests PASSED

- [ ] **Step 2: Final commit with any fixes if needed**

```bash
git add -A
git commit -m "chore: finalize sub-project 1 foundation"
```
