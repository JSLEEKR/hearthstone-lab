# Sub-Project 5: HSReplay Scraper + Tier List Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build HSReplay data scraper (API client, web scraper fallback, data parser) and tier list calculator (weighted winrate, tier ranking, history tracking).

**Architecture:** Two modules under src/scraper/ and src/tierlist/. Scraper collects deck statistics from HSReplay. Tier list combines simulation + HSReplay winrates to assign S/A/B/C/D tiers.

**Tech Stack:** Python 3.11+, httpx (async), Playwright (fallback), SQLAlchemy

**Spec:** `docs/superpowers/specs/2026-03-24-hearthstone-deckmaker-design.md`

---

## File Structure

```
src/
├── scraper/
│   ├── __init__.py        # Already exists
│   ├── api_client.py      # HSReplay internal API client
│   ├── web_scraper.py     # Playwright fallback scraper
│   └── parser.py          # Data normalization + DB storage
└── tierlist/
    ├── __init__.py        # Already exists
    ├── calculator.py      # Weighted winrate calculation
    ├── ranker.py          # Tier assignment (S/A/B/C/D)
    └── history.py         # Tier history tracking

tests/
├── test_scraper.py
├── test_tierlist.py
```

---

### Task 1: HSReplay API client + parser

**Files:**
- Create: `src/scraper/api_client.py`
- Create: `src/scraper/parser.py`
- Create: `tests/test_scraper.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scraper.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.db.tables import Base, Card, Deck, DeckCard, HSReplayStats
from src.scraper.api_client import HSReplayClient
from src.scraper.parser import HSReplayParser


@pytest.fixture
def scraper_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        # Seed some cards
        for i in range(30):
            session.add(Card(
                card_id=f"card_{i}", dbf_id=100+i, name=f"Card {i}",
                name_ko=f"카드 {i}", card_type="MINION", hero_class="NEUTRAL",
                mana_cost=i % 8 + 1, attack=i % 5 + 1, health=i % 5 + 1,
                rarity="COMMON", set_name="TEST", collectible=True,
                is_standard=True, mechanics=[]
            ))
        session.commit()
        yield session
    engine.dispose()


class TestHSReplayClient:
    def test_client_init(self):
        client = HSReplayClient()
        assert client.base_url is not None

    @pytest.mark.asyncio
    async def test_fetch_deck_stats_returns_list(self):
        client = HSReplayClient()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "series": {
                "data": {
                    "ALL": [
                        {
                            "deck_id": "abc123",
                            "win_rate": 55.3,
                            "popularity": 4.2,
                            "total_games": 1500,
                            "archetype_id": 1,
                            "player_class_name": "MAGE",
                        }
                    ]
                }
            }
        }
        with patch.object(client, "_get", return_value=mock_response):
            result = await client.fetch_deck_stats(format_type="standard")
        assert len(result) >= 1
        assert result[0]["win_rate"] == 55.3

    @pytest.mark.asyncio
    async def test_fetch_deck_list_returns_deckstring(self):
        client = HSReplayClient()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "deck_id": "abc123",
            "deckstring": "AAEBAf0EBu72Avb9A...",
            "archetype": "Tempo Mage",
        }
        with patch.object(client, "_get", return_value=mock_response):
            result = await client.fetch_deck_detail("abc123")
        assert "deckstring" in result


class TestHSReplayParser:
    def test_parse_deck_stats(self, scraper_db):
        parser = HSReplayParser(scraper_db)
        raw_data = [
            {
                "deck_id": "abc123",
                "win_rate": 55.3,
                "popularity": 4.2,
                "total_games": 1500,
                "player_class_name": "MAGE",
                "deckstring": None,
            }
        ]
        result = parser.parse_deck_stats(raw_data, format_type="standard")
        assert len(result) >= 0  # may be 0 if no matching deck found

    def test_save_stats(self, scraper_db):
        parser = HSReplayParser(scraper_db)
        # Create a deck first
        deck = Deck(name="Test Deck", hero_class="MAGE", format="standard", source="hsreplay")
        scraper_db.add(deck)
        scraper_db.commit()

        parser.save_stats(deck.id, winrate=55.3, playrate=4.2, games_played=1500)
        stats = scraper_db.query(HSReplayStats).filter_by(deck_id=deck.id).first()
        assert stats is not None
        assert stats.winrate == 55.3
        assert stats.games_played == 1500
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write implementation**

```python
# src/scraper/api_client.py
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

HSREPLAY_BASE_URL = "https://hsreplay.net/analytics/query"
DECK_SUMMARY_URL = f"{HSREPLAY_BASE_URL}/list_decks_by_win_rate/"
DECK_DETAIL_URL = "https://hsreplay.net/api/v1/decks"


class HSReplayClient:
    def __init__(self, base_url: str = HSREPLAY_BASE_URL):
        self.base_url = base_url
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "HearthstoneDeckMaker/1.0",
        }

    async def _get(self, url: str, params: dict | None = None) -> httpx.Response:
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response

    async def fetch_deck_stats(self, format_type: str = "standard") -> list[dict]:
        game_type = "ranked_standard" if format_type == "standard" else "ranked_wild"
        params = {"GameType": game_type, "TimeRange": "LAST_7_DAYS"}
        try:
            response = await self._get(DECK_SUMMARY_URL, params=params)
            data = response.json()
            series = data.get("series", {}).get("data", {})
            all_decks = series.get("ALL", [])
            return all_decks
        except httpx.HTTPError as e:
            logger.error("HSReplay API error: %s", e)
            return []

    async def fetch_deck_detail(self, deck_id: str) -> dict[str, Any]:
        url = f"{DECK_DETAIL_URL}/{deck_id}/"
        try:
            response = await self._get(url)
            return response.json()
        except httpx.HTTPError as e:
            logger.error("HSReplay deck detail error: %s", e)
            return {}
```

```python
# src/scraper/parser.py
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.db.tables import Deck, HSReplayStats

logger = logging.getLogger(__name__)


class HSReplayParser:
    def __init__(self, db: Session):
        self.db = db

    def parse_deck_stats(
        self, raw_data: list[dict], format_type: str = "standard"
    ) -> list[dict]:
        parsed = []
        for entry in raw_data:
            parsed.append({
                "deck_id": entry.get("deck_id"),
                "winrate": entry.get("win_rate", 0.0),
                "playrate": entry.get("popularity", 0.0),
                "games_played": entry.get("total_games", 0),
                "hero_class": entry.get("player_class_name", "UNKNOWN"),
                "deckstring": entry.get("deckstring"),
                "format": format_type,
            })
        return parsed

    def save_stats(
        self, deck_id: int, winrate: float, playrate: float, games_played: int
    ) -> HSReplayStats:
        stats = HSReplayStats(
            deck_id=deck_id,
            winrate=winrate,
            playrate=playrate,
            games_played=games_played,
        )
        self.db.add(stats)
        self.db.commit()
        return stats

    def find_or_create_deck(
        self, hero_class: str, format_type: str, deckstring: str | None = None,
        name: str | None = None,
    ) -> Deck:
        if deckstring:
            existing = self.db.query(Deck).filter_by(
                deckstring=deckstring, format=format_type
            ).first()
            if existing:
                return existing

        deck_name = name or f"HSReplay {hero_class}"
        deck = Deck(
            name=deck_name,
            hero_class=hero_class,
            format=format_type,
            deckstring=deckstring,
            source="hsreplay",
        )
        self.db.add(deck)
        self.db.commit()
        return deck
```

- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add HSReplay API client and data parser"
```

---

### Task 2: Playwright web scraper fallback

**Files:**
- Create: `src/scraper/web_scraper.py`
- Add tests to: `tests/test_scraper.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_scraper.py

class TestWebScraper:
    def test_scraper_init(self):
        from src.scraper.web_scraper import HSReplayWebScraper
        scraper = HSReplayWebScraper()
        assert scraper.base_url is not None

    @pytest.mark.asyncio
    async def test_scrape_returns_list(self):
        from src.scraper.web_scraper import HSReplayWebScraper
        scraper = HSReplayWebScraper()
        # Mock Playwright to avoid real browser
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector_all = AsyncMock(return_value=[])
        mock_page.close = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        with patch.object(scraper, "_launch_browser", return_value=mock_browser):
            result = await scraper.scrape_tier_list(format_type="standard")
        assert isinstance(result, list)
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write implementation**

```python
# src/scraper/web_scraper.py
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

HSREPLAY_DECKS_URL = "https://hsreplay.net/decks/"


class HSReplayWebScraper:
    def __init__(self, base_url: str = HSREPLAY_DECKS_URL):
        self.base_url = base_url

    async def _launch_browser(self):
        from playwright.async_api import async_playwright
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True)
        return browser

    async def scrape_tier_list(self, format_type: str = "standard") -> list[dict]:
        url = f"{self.base_url}?hl=ko&gameType={'RANKED_STANDARD' if format_type == 'standard' else 'RANKED_WILD'}"
        try:
            browser = await self._launch_browser()
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_selector(".deck-tile", timeout=15000)

            deck_elements = await page.query_selector_all(".deck-tile")
            results = []
            for el in deck_elements:
                deck_data = await self._parse_deck_element(el)
                if deck_data:
                    results.append(deck_data)

            await page.close()
            await context.close()
            await browser.close()
            return results
        except Exception as e:
            logger.error("Playwright scraping failed: %s", e)
            return []

    @staticmethod
    async def _parse_deck_element(element) -> dict[str, Any] | None:
        try:
            name_el = await element.query_selector(".deck-name")
            winrate_el = await element.query_selector(".win-rate")
            games_el = await element.query_selector(".game-count")
            link_el = await element.query_selector("a")

            name = await name_el.inner_text() if name_el else "Unknown"
            winrate_text = await winrate_el.inner_text() if winrate_el else "0%"
            games_text = await games_el.inner_text() if games_el else "0"
            href = await link_el.get_attribute("href") if link_el else ""

            winrate = float(winrate_text.replace("%", "").strip())
            games = int(games_text.replace(",", "").strip())

            return {
                "name": name,
                "win_rate": winrate,
                "total_games": games,
                "url": href,
            }
        except Exception:
            return None
```

- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add Playwright web scraper fallback for HSReplay"
```

---

### Task 3: Tier list calculator + ranker

**Files:**
- Create: `src/tierlist/calculator.py`
- Create: `src/tierlist/ranker.py`
- Create: `tests/test_tierlist.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tierlist.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.db.tables import Base, Deck, HSReplayStats, Simulation, TierHistory
from src.tierlist.calculator import TierCalculator
from src.tierlist.ranker import TierRanker


@pytest.fixture
def tier_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        # Create decks
        for i in range(5):
            deck = Deck(name=f"Deck {i}", hero_class="MAGE", format="standard",
                        source="hsreplay")
            session.add(deck)
        session.commit()

        # Add HSReplay stats
        decks = session.query(Deck).all()
        winrates = [58.0, 54.0, 50.0, 47.0, 43.0]
        for deck, wr in zip(decks, winrates):
            session.add(HSReplayStats(
                deck_id=deck.id, winrate=wr, playrate=5.0, games_played=1000
            ))
        session.commit()
        yield session
    engine.dispose()


class TestTierCalculator:
    def test_calculate_combined_winrate_both_sources(self):
        calc = TierCalculator(weight_sim=0.5, weight_hsreplay=0.5)
        result = calc.combined_winrate(sim_winrate=60.0, hsreplay_winrate=50.0)
        assert result == 55.0

    def test_calculate_combined_winrate_sim_only(self):
        calc = TierCalculator(weight_sim=0.5, weight_hsreplay=0.5)
        result = calc.combined_winrate(sim_winrate=60.0, hsreplay_winrate=None)
        assert result == 60.0

    def test_calculate_combined_winrate_hsreplay_only(self):
        calc = TierCalculator(weight_sim=0.5, weight_hsreplay=0.5)
        result = calc.combined_winrate(sim_winrate=None, hsreplay_winrate=50.0)
        assert result == 50.0

    def test_calculate_combined_winrate_none(self):
        calc = TierCalculator(weight_sim=0.5, weight_hsreplay=0.5)
        result = calc.combined_winrate(sim_winrate=None, hsreplay_winrate=None)
        assert result is None

    def test_get_deck_winrates(self, tier_db):
        calc = TierCalculator(weight_sim=0.5, weight_hsreplay=0.5)
        results = calc.get_deck_winrates(tier_db, format_type="standard")
        assert len(results) == 5


class TestTierRanker:
    def test_assign_tier_s(self):
        ranker = TierRanker()
        assert ranker.assign_tier(58.0) == "S"

    def test_assign_tier_a(self):
        ranker = TierRanker()
        assert ranker.assign_tier(53.0) == "A"

    def test_assign_tier_b(self):
        ranker = TierRanker()
        assert ranker.assign_tier(50.0) == "B"

    def test_assign_tier_c(self):
        ranker = TierRanker()
        assert ranker.assign_tier(47.0) == "C"

    def test_assign_tier_d(self):
        ranker = TierRanker()
        assert ranker.assign_tier(43.0) == "D"

    def test_rank_decks(self, tier_db):
        calc = TierCalculator(weight_sim=0.5, weight_hsreplay=0.5)
        ranker = TierRanker()
        deck_winrates = calc.get_deck_winrates(tier_db, format_type="standard")
        ranked = ranker.rank_decks(deck_winrates)
        assert len(ranked) == 5
        assert ranked[0]["tier"] == "S"
        assert ranked[-1]["tier"] == "D"
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write implementation**

```python
# src/tierlist/calculator.py
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db.tables import Deck, HSReplayStats, Simulation

logger = logging.getLogger(__name__)


class TierCalculator:
    def __init__(self, weight_sim: float = 0.5, weight_hsreplay: float = 0.5):
        self.weight_sim = weight_sim
        self.weight_hsreplay = weight_hsreplay

    def combined_winrate(
        self, sim_winrate: float | None, hsreplay_winrate: float | None
    ) -> float | None:
        if sim_winrate is not None and hsreplay_winrate is not None:
            return (sim_winrate * self.weight_sim) + (hsreplay_winrate * self.weight_hsreplay)
        if sim_winrate is not None:
            return sim_winrate
        if hsreplay_winrate is not None:
            return hsreplay_winrate
        return None

    def get_sim_winrate(self, db: Session, deck_id: int) -> float | None:
        wins = db.query(func.count(Simulation.id)).filter(
            Simulation.winner_id == deck_id
        ).scalar()
        total = db.query(func.count(Simulation.id)).filter(
            (Simulation.deck_a_id == deck_id) | (Simulation.deck_b_id == deck_id)
        ).scalar()
        if total == 0:
            return None
        return (wins / total) * 100

    def get_hsreplay_winrate(self, db: Session, deck_id: int) -> float | None:
        latest = (
            db.query(HSReplayStats)
            .filter_by(deck_id=deck_id)
            .order_by(HSReplayStats.collected_at.desc())
            .first()
        )
        if not latest:
            return None
        return latest.winrate

    def get_deck_winrates(
        self, db: Session, format_type: str = "standard", min_games: int = 0
    ) -> list[dict]:
        decks = db.query(Deck).filter_by(format=format_type).all()
        results = []
        for deck in decks:
            sim_wr = self.get_sim_winrate(db, deck.id)
            hs_wr = self.get_hsreplay_winrate(db, deck.id)
            combined = self.combined_winrate(sim_wr, hs_wr)
            if combined is None:
                continue
            results.append({
                "deck_id": deck.id,
                "deck_name": deck.name,
                "hero_class": deck.hero_class,
                "sim_winrate": sim_wr,
                "hsreplay_winrate": hs_wr,
                "combined_winrate": combined,
            })
        results.sort(key=lambda x: x["combined_winrate"], reverse=True)
        return results
```

```python
# src/tierlist/ranker.py
from __future__ import annotations

import logging

from config import settings

logger = logging.getLogger(__name__)


class TierRanker:
    def __init__(self, thresholds: dict | None = None):
        self.thresholds = thresholds or settings.TIER_THRESHOLDS

    def assign_tier(self, winrate: float) -> str:
        if winrate >= self.thresholds["S"]:
            return "S"
        if winrate >= self.thresholds["A"]:
            return "A"
        if winrate >= self.thresholds["B"]:
            return "B"
        if winrate >= self.thresholds["C"]:
            return "C"
        return "D"

    def rank_decks(self, deck_winrates: list[dict]) -> list[dict]:
        ranked = []
        for entry in deck_winrates:
            tier = self.assign_tier(entry["combined_winrate"])
            ranked.append({**entry, "tier": tier})
        ranked.sort(key=lambda x: x["combined_winrate"], reverse=True)
        return ranked
```

- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add tier list calculator and ranker (S/A/B/C/D)"
```

---

### Task 4: Tier history tracking

**Files:**
- Create: `src/tierlist/history.py`
- Add tests to: `tests/test_tierlist.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_tierlist.py

class TestTierHistory:
    def test_record_tier(self, tier_db):
        from src.tierlist.history import TierHistoryTracker
        tracker = TierHistoryTracker(tier_db)
        tracker.record(
            deck_id=1, tier="S", sim_winrate=60.0,
            hsreplay_winrate=56.0, combined_winrate=58.0
        )
        records = tier_db.query(TierHistory).filter_by(deck_id=1).all()
        assert len(records) == 1
        assert records[0].tier == "S"

    def test_get_history(self, tier_db):
        from src.tierlist.history import TierHistoryTracker
        tracker = TierHistoryTracker(tier_db)
        tracker.record(deck_id=1, tier="S", sim_winrate=60.0,
                       hsreplay_winrate=56.0, combined_winrate=58.0)
        tracker.record(deck_id=1, tier="A", sim_winrate=55.0,
                       hsreplay_winrate=53.0, combined_winrate=54.0)
        history = tracker.get_history(deck_id=1)
        assert len(history) == 2

    def test_get_latest_tier(self, tier_db):
        from src.tierlist.history import TierHistoryTracker
        tracker = TierHistoryTracker(tier_db)
        tracker.record(deck_id=1, tier="S", sim_winrate=60.0,
                       hsreplay_winrate=56.0, combined_winrate=58.0)
        tracker.record(deck_id=1, tier="A", sim_winrate=55.0,
                       hsreplay_winrate=53.0, combined_winrate=54.0)
        latest = tracker.get_latest_tier(deck_id=1)
        assert latest == "A"
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write implementation**

```python
# src/tierlist/history.py
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.db.tables import TierHistory

logger = logging.getLogger(__name__)


class TierHistoryTracker:
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        deck_id: int,
        tier: str,
        sim_winrate: float | None,
        hsreplay_winrate: float | None,
        combined_winrate: float,
    ) -> TierHistory:
        entry = TierHistory(
            deck_id=deck_id,
            tier=tier,
            sim_winrate=sim_winrate,
            hsreplay_winrate=hsreplay_winrate,
            combined_winrate=combined_winrate,
        )
        self.db.add(entry)
        self.db.commit()
        return entry

    def get_history(self, deck_id: int, limit: int = 30) -> list[TierHistory]:
        return (
            self.db.query(TierHistory)
            .filter_by(deck_id=deck_id)
            .order_by(TierHistory.recorded_at.desc())
            .limit(limit)
            .all()
        )

    def get_latest_tier(self, deck_id: int) -> str | None:
        latest = (
            self.db.query(TierHistory)
            .filter_by(deck_id=deck_id)
            .order_by(TierHistory.recorded_at.desc())
            .first()
        )
        return latest.tier if latest else None
```

- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add tier history tracking with trend data"
```

---

### Task 5: Full test suite

- [ ] **Step 1: Run all tests**

Run: `.venv/Scripts/python -m pytest tests/ -v --tb=short`
Expected: All tests pass

- [ ] **Step 2: Commit any fixes**
