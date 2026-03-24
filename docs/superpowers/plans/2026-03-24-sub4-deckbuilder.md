# Sub-Project 4: Deck Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build manual deck builder (card search/filter, add/remove, validation, deckstring import/export) and AI auto deck generator (synergy analysis, mana curve optimization, archetype classification).

**Architecture:** Three modules under src/deckbuilder/. Manual builder provides CRUD operations on deck composition. Auto builder generates decks using heuristic scoring. Archetype classifier assigns decks to aggro/midrange/control/combo.

**Tech Stack:** Python 3.11+, SQLAlchemy, base64 (deckstring encoding)

**Spec:** `docs/superpowers/specs/2026-03-24-hearthstone-deckmaker-design.md`

---

## File Structure

```
src/
├── core/
│   └── deckstring.py     # Implement deckstring encode/decode (currently stub)
└── deckbuilder/
    ├── __init__.py
    ├── manual.py          # Card search/filter, deck CRUD, validation
    ├── auto.py            # AI deck generation with synergy scoring
    └── archetypes.py      # Deck archetype classification

tests/
├── test_deckstring.py
├── test_manual_builder.py
├── test_auto_builder.py
└── test_archetypes.py
```

---

### Task 1: Deckstring encode/decode

**Files:**
- Modify: `src/core/deckstring.py` (replace stub)
- Create: `tests/test_deckstring.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_deckstring.py
import pytest
from src.core.deckstring import encode_deckstring, decode_deckstring


class TestDeckstring:
    def test_encode_and_decode_roundtrip(self):
        hero_id = 274  # Jaina (Mage)
        card_dbf_ids = {
            522: 2,    # Fireball x2
            1369: 2,   # Chillwind Yeti x2
            179: 1,    # Archmage Antonidas x1 (legendary)
        }
        format_type = 2  # standard

        encoded = encode_deckstring(hero_id, card_dbf_ids, format_type)
        assert isinstance(encoded, str)

        result = decode_deckstring(encoded)
        assert result["hero"] == hero_id
        assert result["format"] == format_type
        assert result["cards"] == card_dbf_ids

    def test_decode_known_deckstring(self):
        # A simple known deckstring structure
        hero_id = 274
        cards = {522: 2, 1369: 2}
        encoded = encode_deckstring(hero_id, cards, 2)
        decoded = decode_deckstring(encoded)
        assert decoded["hero"] == 274
        assert decoded["cards"][522] == 2
        assert decoded["cards"][1369] == 2

    def test_encode_empty_deck(self):
        encoded = encode_deckstring(274, {}, 2)
        decoded = decode_deckstring(encoded)
        assert decoded["hero"] == 274
        assert decoded["cards"] == {}

    def test_encode_separates_single_and_double(self):
        cards = {100: 1, 200: 2, 300: 1}
        encoded = encode_deckstring(274, cards, 2)
        decoded = decode_deckstring(encoded)
        assert decoded["cards"][100] == 1
        assert decoded["cards"][200] == 2
        assert decoded["cards"][300] == 1
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write implementation**

```python
# src/core/deckstring.py
"""Deckstring encode/decode compatible with Hearthstone deck codes.

Format: base64 encoded varint stream.
Structure: [reserved=0] [version=1] [format] [1 hero] [single-copy cards] [double-copy cards]
"""
from __future__ import annotations

import base64
from io import BytesIO


def _write_varint(stream: BytesIO, value: int):
    while value > 0x7F:
        stream.write(bytes([0x80 | (value & 0x7F)]))
        value >>= 7
    stream.write(bytes([value & 0x7F]))


def _read_varint(stream: BytesIO) -> int:
    result = 0
    shift = 0
    while True:
        byte = stream.read(1)
        if not byte:
            raise ValueError("Unexpected end of stream")
        b = byte[0]
        result |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            break
        shift += 7
    return result


def encode_deckstring(hero_dbf_id: int, card_dbf_ids: dict[int, int], format_type: int = 2) -> str:
    """Encode a deck into a deckstring.

    Args:
        hero_dbf_id: Hero's DBF ID
        card_dbf_ids: Dict of {card_dbf_id: count}
        format_type: 1=wild, 2=standard

    Returns:
        Base64 encoded deckstring
    """
    singles = sorted([dbf for dbf, count in card_dbf_ids.items() if count == 1])
    doubles = sorted([dbf for dbf, count in card_dbf_ids.items() if count == 2])

    stream = BytesIO()
    _write_varint(stream, 0)  # reserved
    _write_varint(stream, 1)  # version
    _write_varint(stream, format_type)

    # Heroes
    _write_varint(stream, 1)  # hero count
    _write_varint(stream, hero_dbf_id)

    # Single-copy cards
    _write_varint(stream, len(singles))
    for dbf in singles:
        _write_varint(stream, dbf)

    # Double-copy cards
    _write_varint(stream, len(doubles))
    for dbf in doubles:
        _write_varint(stream, dbf)

    # N-copy cards (count > 2)
    n_copies = [(dbf, count) for dbf, count in card_dbf_ids.items() if count > 2]
    _write_varint(stream, len(n_copies))
    for dbf, count in sorted(n_copies):
        _write_varint(stream, dbf)
        _write_varint(stream, count)

    return base64.b64encode(stream.getvalue()).decode("ascii")


def decode_deckstring(deckstring: str) -> dict:
    """Decode a deckstring into hero, format, and cards.

    Returns:
        {"hero": int, "format": int, "cards": {dbf_id: count}}
    """
    data = base64.b64decode(deckstring)
    stream = BytesIO(data)

    _read_varint(stream)  # reserved
    _read_varint(stream)  # version
    format_type = _read_varint(stream)

    hero_count = _read_varint(stream)
    heroes = [_read_varint(stream) for _ in range(hero_count)]

    cards: dict[int, int] = {}

    single_count = _read_varint(stream)
    for _ in range(single_count):
        dbf = _read_varint(stream)
        cards[dbf] = 1

    double_count = _read_varint(stream)
    for _ in range(double_count):
        dbf = _read_varint(stream)
        cards[dbf] = 2

    n_count = _read_varint(stream)
    for _ in range(n_count):
        dbf = _read_varint(stream)
        count = _read_varint(stream)
        cards[dbf] = count

    return {
        "hero": heroes[0] if heroes else 0,
        "format": format_type,
        "cards": cards,
    }
```

- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

```bash
git commit -m "feat: implement deckstring encode/decode with varint format"
```

---

### Task 2: Manual deck builder

**Files:**
- Create: `src/deckbuilder/manual.py`
- Create: `tests/test_manual_builder.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_manual_builder.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.db.tables import Base, Card, Deck, DeckCard
from src.deckbuilder.manual import ManualDeckBuilder


@pytest.fixture
def builder_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        # Seed cards
        cards = [
            Card(card_id=f"card_{i}", dbf_id=100+i, name=f"Card {i}",
                 name_ko=f"카드 {i}", card_type="MINION", hero_class="NEUTRAL",
                 mana_cost=i % 8 + 1, attack=i % 5 + 1, health=i % 5 + 1,
                 rarity="COMMON" if i < 28 else "LEGENDARY",
                 set_name="TEST", collectible=True, is_standard=True,
                 mechanics=[])
            for i in range(30)
        ]
        # Add class-specific cards
        mage_card = Card(card_id="mage_1", dbf_id=200, name="Mage Spell",
                         name_ko="메이지 주문", card_type="SPELL", hero_class="MAGE",
                         mana_cost=3, rarity="RARE", set_name="TEST",
                         collectible=True, is_standard=True, mechanics=[])
        cards.append(mage_card)
        session.add_all(cards)
        session.commit()
        yield session
    engine.dispose()


class TestManualDeckBuilder:
    def test_search_cards_by_name(self, builder_db):
        builder = ManualDeckBuilder(builder_db)
        results = builder.search_cards(query="Card 1")
        assert len(results) >= 1
        assert any(c.name == "Card 1" for c in results)

    def test_search_cards_by_class(self, builder_db):
        builder = ManualDeckBuilder(builder_db)
        results = builder.search_cards(hero_class="MAGE")
        # Should return MAGE + NEUTRAL cards
        assert any(c.hero_class == "MAGE" for c in results)
        assert any(c.hero_class == "NEUTRAL" for c in results)

    def test_search_cards_by_mana_cost(self, builder_db):
        builder = ManualDeckBuilder(builder_db)
        results = builder.search_cards(mana_cost=3)
        assert all(c.mana_cost == 3 for c in results)

    def test_create_deck(self, builder_db):
        builder = ManualDeckBuilder(builder_db)
        deck = builder.create_deck(name="Test Deck", hero_class="MAGE", format="standard")
        assert deck.id is not None
        assert deck.hero_class == "MAGE"

    def test_add_card_to_deck(self, builder_db):
        builder = ManualDeckBuilder(builder_db)
        deck = builder.create_deck(name="Test", hero_class="MAGE", format="standard")
        result = builder.add_card(deck.id, "card_0")
        assert result is True

    def test_add_card_twice(self, builder_db):
        builder = ManualDeckBuilder(builder_db)
        deck = builder.create_deck(name="Test", hero_class="MAGE", format="standard")
        builder.add_card(deck.id, "card_0")
        result = builder.add_card(deck.id, "card_0")
        assert result is True  # now count=2

    def test_add_legendary_twice_fails(self, builder_db):
        builder = ManualDeckBuilder(builder_db)
        deck = builder.create_deck(name="Test", hero_class="MAGE", format="standard")
        builder.add_card(deck.id, "card_28")  # legendary
        result = builder.add_card(deck.id, "card_28")
        assert result is False

    def test_remove_card(self, builder_db):
        builder = ManualDeckBuilder(builder_db)
        deck = builder.create_deck(name="Test", hero_class="MAGE", format="standard")
        builder.add_card(deck.id, "card_0")
        result = builder.remove_card(deck.id, "card_0")
        assert result is True

    def test_get_deck_cards(self, builder_db):
        builder = ManualDeckBuilder(builder_db)
        deck = builder.create_deck(name="Test", hero_class="MAGE", format="standard")
        builder.add_card(deck.id, "card_0")
        builder.add_card(deck.id, "card_0")
        builder.add_card(deck.id, "card_1")
        cards = builder.get_deck_cards(deck.id)
        assert len(cards) == 2  # 2 distinct cards
        assert any(c["count"] == 2 for c in cards)
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write implementation**

```python
# src/deckbuilder/manual.py
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.db.tables import Card, Deck, DeckCard

logger = logging.getLogger(__name__)


class ManualDeckBuilder:
    def __init__(self, db: Session):
        self.db = db

    def search_cards(
        self,
        query: str | None = None,
        hero_class: str | None = None,
        mana_cost: int | None = None,
        rarity: str | None = None,
        set_name: str | None = None,
        collectible: bool = True,
    ) -> list[Card]:
        q = self.db.query(Card).filter(Card.collectible == collectible)

        if query:
            q = q.filter(Card.name.ilike(f"%{query}%") | Card.name_ko.ilike(f"%{query}%"))
        if hero_class:
            q = q.filter(Card.hero_class.in_([hero_class, "NEUTRAL"]))
        if mana_cost is not None:
            q = q.filter(Card.mana_cost == mana_cost)
        if rarity:
            q = q.filter(Card.rarity == rarity)
        if set_name:
            q = q.filter(Card.set_name == set_name)

        return q.order_by(Card.mana_cost, Card.name).all()

    def create_deck(self, name: str, hero_class: str, format: str) -> Deck:
        deck = Deck(name=name, hero_class=hero_class, format=format, source="manual")
        self.db.add(deck)
        self.db.commit()
        return deck

    def add_card(self, deck_id: int, card_id: str) -> bool:
        card = self.db.query(Card).filter_by(card_id=card_id).first()
        if not card:
            return False

        existing = self.db.query(DeckCard).filter_by(
            deck_id=deck_id, card_id=card.id
        ).first()

        if existing:
            max_count = 1 if card.rarity == "LEGENDARY" else 2
            if existing.count >= max_count:
                return False
            existing.count += 1
        else:
            dc = DeckCard(deck_id=deck_id, card_id=card.id, count=1)
            self.db.add(dc)

        self.db.commit()
        return True

    def remove_card(self, deck_id: int, card_id: str) -> bool:
        card = self.db.query(Card).filter_by(card_id=card_id).first()
        if not card:
            return False

        existing = self.db.query(DeckCard).filter_by(
            deck_id=deck_id, card_id=card.id
        ).first()

        if not existing:
            return False

        if existing.count > 1:
            existing.count -= 1
        else:
            self.db.delete(existing)

        self.db.commit()
        return True

    def get_deck_cards(self, deck_id: int) -> list[dict]:
        results = (
            self.db.query(DeckCard, Card)
            .join(Card, DeckCard.card_id == Card.id)
            .filter(DeckCard.deck_id == deck_id)
            .order_by(Card.mana_cost, Card.name)
            .all()
        )
        return [
            {
                "card_id": card.card_id,
                "name": card.name,
                "name_ko": card.name_ko,
                "mana_cost": card.mana_cost,
                "count": dc.count,
                "rarity": card.rarity,
                "card_type": card.card_type,
            }
            for dc, card in results
        ]
```

- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add manual deck builder with card search and deck CRUD"
```

---

### Task 3: Archetype classification

**Files:**
- Create: `src/deckbuilder/archetypes.py`
- Create: `tests/test_archetypes.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_archetypes.py
from src.deckbuilder.archetypes import classify_archetype


def _make_deck_stats(avg_cost: float, spell_ratio: float, has_combo_pieces: bool = False):
    return {"avg_mana_cost": avg_cost, "spell_ratio": spell_ratio,
            "has_combo_pieces": has_combo_pieces}


class TestArchetypeClassification:
    def test_aggro_low_curve(self):
        result = classify_archetype(_make_deck_stats(avg_cost=2.0, spell_ratio=0.2))
        assert result == "aggro"

    def test_control_high_curve(self):
        result = classify_archetype(_make_deck_stats(avg_cost=5.5, spell_ratio=0.4))
        assert result == "control"

    def test_midrange_medium_curve(self):
        result = classify_archetype(_make_deck_stats(avg_cost=3.5, spell_ratio=0.3))
        assert result == "midrange"

    def test_combo_with_combo_pieces(self):
        result = classify_archetype(_make_deck_stats(avg_cost=4.0, spell_ratio=0.5,
                                                      has_combo_pieces=True))
        assert result == "combo"

    def test_classify_from_card_list(self):
        from src.deckbuilder.archetypes import classify_from_cards
        cards = [
            {"mana_cost": 1, "card_type": "MINION", "count": 2},
            {"mana_cost": 2, "card_type": "MINION", "count": 2},
            {"mana_cost": 1, "card_type": "SPELL", "count": 2},
            {"mana_cost": 3, "card_type": "MINION", "count": 2},
        ]
        result = classify_from_cards(cards)
        assert result in ("aggro", "midrange", "control", "combo")
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write implementation**

```python
# src/deckbuilder/archetypes.py
from __future__ import annotations

AGGRO_MAX_AVG_COST = 3.0
MIDRANGE_MAX_AVG_COST = 4.5
COMBO_SPELL_RATIO = 0.45


def classify_archetype(deck_stats: dict) -> str:
    avg_cost = deck_stats.get("avg_mana_cost", 0)
    spell_ratio = deck_stats.get("spell_ratio", 0)
    has_combo = deck_stats.get("has_combo_pieces", False)

    if has_combo and spell_ratio >= COMBO_SPELL_RATIO:
        return "combo"
    if avg_cost <= AGGRO_MAX_AVG_COST:
        return "aggro"
    if avg_cost <= MIDRANGE_MAX_AVG_COST:
        return "midrange"
    return "control"


def classify_from_cards(cards: list[dict]) -> str:
    if not cards:
        return "midrange"

    total_cost = 0
    total_cards = 0
    spell_count = 0

    for c in cards:
        count = c.get("count", 1)
        total_cost += c.get("mana_cost", 0) * count
        total_cards += count
        if c.get("card_type") == "SPELL":
            spell_count += count

    avg_cost = total_cost / total_cards if total_cards > 0 else 0
    spell_ratio = spell_count / total_cards if total_cards > 0 else 0

    return classify_archetype({
        "avg_mana_cost": avg_cost,
        "spell_ratio": spell_ratio,
        "has_combo_pieces": False,
    })
```

- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add deck archetype classification (aggro/midrange/control/combo)"
```

---

### Task 4: AI auto deck builder

**Files:**
- Create: `src/deckbuilder/auto.py`
- Create: `tests/test_auto_builder.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_auto_builder.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.db.tables import Base, Card
from src.deckbuilder.auto import AutoDeckBuilder


@pytest.fixture
def auto_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        cards = []
        for i in range(50):
            cards.append(Card(
                card_id=f"card_{i}", dbf_id=100+i, name=f"Card {i}",
                name_ko=f"카드 {i}", card_type="MINION", hero_class="NEUTRAL",
                mana_cost=i % 8 + 1, attack=i % 5 + 1, health=i % 5 + 1,
                rarity="COMMON" if i < 45 else "LEGENDARY",
                set_name="TEST", collectible=True, is_standard=True,
                mechanics=[]
            ))
        for i in range(10):
            cards.append(Card(
                card_id=f"mage_{i}", dbf_id=200+i, name=f"Mage Card {i}",
                name_ko=f"메이지 카드 {i}", card_type="SPELL" if i < 5 else "MINION",
                hero_class="MAGE", mana_cost=i % 6 + 1, attack=None if i < 5 else i,
                health=None if i < 5 else i + 1,
                rarity="COMMON", set_name="TEST", collectible=True,
                is_standard=True, mechanics=[]
            ))
        session.add_all(cards)
        session.commit()
        yield session
    engine.dispose()


class TestAutoDeckBuilder:
    def test_generate_deck_has_30_cards(self, auto_db):
        builder = AutoDeckBuilder(auto_db)
        deck = builder.generate_deck(hero_class="MAGE", format="standard")
        total = sum(c["count"] for c in deck["cards"])
        assert total == 30

    def test_generate_deck_correct_class(self, auto_db):
        builder = AutoDeckBuilder(auto_db)
        deck = builder.generate_deck(hero_class="MAGE", format="standard")
        assert deck["hero_class"] == "MAGE"

    def test_generate_deck_respects_legendary_limit(self, auto_db):
        builder = AutoDeckBuilder(auto_db)
        deck = builder.generate_deck(hero_class="MAGE", format="standard")
        for c in deck["cards"]:
            if c["rarity"] == "LEGENDARY":
                assert c["count"] == 1

    def test_generate_deck_has_mana_curve(self, auto_db):
        builder = AutoDeckBuilder(auto_db)
        deck = builder.generate_deck(hero_class="MAGE", format="standard")
        costs = {}
        for c in deck["cards"]:
            cost = c["mana_cost"]
            costs[cost] = costs.get(cost, 0) + c["count"]
        # Should have cards at multiple mana costs
        assert len(costs) >= 3

    def test_generate_aggro_deck_low_curve(self, auto_db):
        builder = AutoDeckBuilder(auto_db)
        deck = builder.generate_deck(hero_class="MAGE", format="standard",
                                      archetype="aggro")
        total_cost = sum(c["mana_cost"] * c["count"] for c in deck["cards"])
        total_cards = sum(c["count"] for c in deck["cards"])
        avg = total_cost / total_cards
        assert avg <= 4.0  # aggro should have low avg cost
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write implementation**

```python
# src/deckbuilder/auto.py
from __future__ import annotations

import logging
import random

from sqlalchemy.orm import Session

from src.db.tables import Card
from src.deckbuilder.archetypes import classify_from_cards

logger = logging.getLogger(__name__)

DECK_SIZE = 30

# Ideal mana curve weights by cost (how many cards at each cost)
CURVE_TARGETS = {
    "aggro":    {1: 6, 2: 8, 3: 6, 4: 4, 5: 2, 6: 2, 7: 1, 8: 1},
    "midrange": {1: 3, 2: 5, 3: 6, 4: 6, 5: 4, 6: 3, 7: 2, 8: 1},
    "control":  {1: 2, 2: 4, 3: 4, 4: 4, 5: 4, 6: 4, 7: 4, 8: 4},
}


class AutoDeckBuilder:
    def __init__(self, db: Session):
        self.db = db

    def generate_deck(
        self,
        hero_class: str,
        format: str = "standard",
        archetype: str | None = None,
    ) -> dict:
        # Get available cards
        q = self.db.query(Card).filter(
            Card.collectible == True,
            Card.hero_class.in_([hero_class, "NEUTRAL"]),
        )
        if format == "standard":
            q = q.filter(Card.is_standard == True)

        available = q.all()

        if not archetype:
            archetype = "midrange"

        curve = CURVE_TARGETS.get(archetype, CURVE_TARGETS["midrange"])

        # Score and select cards
        deck_cards: dict[int, dict] = {}  # card.id -> {card_data, count}
        total = 0

        # Group by mana cost
        by_cost: dict[int, list[Card]] = {}
        for card in available:
            cost = min(card.mana_cost, 8)  # group 8+ together
            if cost not in by_cost:
                by_cost[cost] = []
            by_cost[cost].append(card)

        # Fill curve
        for cost in sorted(curve.keys()):
            target = curve[cost]
            pool = by_cost.get(cost, [])
            if not pool:
                continue

            # Prioritize class cards
            class_cards = [c for c in pool if c.hero_class == hero_class]
            neutral_cards = [c for c in pool if c.hero_class == "NEUTRAL"]

            # Score: class cards first, then by stat efficiency
            scored = []
            for c in class_cards:
                scored.append((c, self._score_card(c, archetype) + 5))
            for c in neutral_cards:
                scored.append((c, self._score_card(c, archetype)))

            scored.sort(key=lambda x: x[1], reverse=True)

            added_at_cost = 0
            for card, score in scored:
                if total >= DECK_SIZE or added_at_cost >= target:
                    break

                max_copies = 1 if card.rarity == "LEGENDARY" else 2
                current = deck_cards.get(card.id, {}).get("count", 0)
                copies_to_add = min(max_copies - current, target - added_at_cost, DECK_SIZE - total)

                if copies_to_add > 0:
                    if card.id not in deck_cards:
                        deck_cards[card.id] = {
                            "card_id": card.card_id,
                            "name": card.name,
                            "name_ko": card.name_ko,
                            "mana_cost": card.mana_cost,
                            "rarity": card.rarity,
                            "card_type": card.card_type,
                            "count": copies_to_add,
                        }
                    else:
                        deck_cards[card.id]["count"] += copies_to_add

                    total += copies_to_add
                    added_at_cost += copies_to_add

        # If we still need more cards, fill randomly
        if total < DECK_SIZE:
            remaining = [c for c in available if c.id not in deck_cards]
            random.shuffle(remaining)
            for card in remaining:
                if total >= DECK_SIZE:
                    break
                max_copies = 1 if card.rarity == "LEGENDARY" else 2
                copies = min(max_copies, DECK_SIZE - total)
                deck_cards[card.id] = {
                    "card_id": card.card_id,
                    "name": card.name,
                    "name_ko": card.name_ko,
                    "mana_cost": card.mana_cost,
                    "rarity": card.rarity,
                    "card_type": card.card_type,
                    "count": copies,
                }
                total += copies

        cards_list = list(deck_cards.values())
        detected_archetype = classify_from_cards(cards_list)

        return {
            "hero_class": hero_class,
            "format": format,
            "archetype": detected_archetype,
            "cards": cards_list,
        }

    @staticmethod
    def _score_card(card: Card, archetype: str) -> float:
        score = 0.0
        if card.card_type == "MINION":
            attack = card.attack or 0
            health = card.health or 0
            cost = max(card.mana_cost, 1)
            score = (attack + health) / cost

            if archetype == "aggro":
                score += attack / cost
            elif archetype == "control":
                score += health / cost
        elif card.card_type == "SPELL":
            score = 3.0 / max(card.mana_cost, 1)
        return score
```

- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add AI auto deck builder with mana curve optimization"
```

---

### Task 5: Full test suite

- [ ] **Step 1: Run all tests**

Run: `.venv/Scripts/python -m pytest tests/ -v --tb=short`
Expected: All tests pass

- [ ] **Step 2: Commit any fixes**
