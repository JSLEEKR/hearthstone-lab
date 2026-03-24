# Sub-Project 2: Card Data Collector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the card data collection pipeline that fetches all Hearthstone cards from HearthstoneJSON (primary) and Blizzard API (secondary), merges them into the database, and caches card images locally.

**Architecture:** Three collector modules (hearthstone_json, blizzard_api, sync) plus an image cache module. All use httpx async client. Data flows into the cards table via SQLAlchemy ORM.

**Tech Stack:** httpx (async HTTP), SQLAlchemy, Pillow, asyncio

**Spec:** `docs/superpowers/specs/2026-03-24-hearthstone-deckmaker-design.md`

---

## File Structure

```
src/collector/
├── __init__.py
├── hearthstone_json.py   # HearthstoneJSON API client
├── blizzard_api.py       # Blizzard API client (OAuth + card fetch)
├── sync.py               # Merge two sources, upsert to DB
└── image_cache.py        # Download and cache card images

tests/
├── test_hearthstone_json.py
├── test_blizzard_api.py
├── test_sync.py
└── test_image_cache.py
```

---

### Task 1: HearthstoneJSON API client

**Files:**
- Create: `src/collector/hearthstone_json.py`
- Create: `tests/test_hearthstone_json.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_hearthstone_json.py
import pytest
from unittest.mock import AsyncMock, patch
from src.collector.hearthstone_json import HearthstoneJsonClient


SAMPLE_CARDS_KO = [
    {
        "id": "CS2_182",
        "dbfId": 1369,
        "name": "칠풍의 예티",
        "type": "MINION",
        "cardClass": "NEUTRAL",
        "cost": 4,
        "attack": 4,
        "health": 5,
        "rarity": "FREE",
        "set": "CORE",
        "collectible": True,
        "text": "",
        "mechanics": [],
    },
    {
        "id": "CS2_029",
        "dbfId": 522,
        "name": "화염구",
        "type": "SPELL",
        "cardClass": "MAGE",
        "cost": 4,
        "rarity": "FREE",
        "set": "CORE",
        "collectible": True,
        "text": "피해를 <b>6</b>만큼 줍니다.",
        "mechanics": [],
    },
    {
        "id": "HIDDEN_001",
        "dbfId": 9999,
        "name": "숨겨진카드",
        "type": "ENCHANTMENT",
        "cardClass": "NEUTRAL",
        "cost": 0,
        "set": "CORE",
    },
]

SAMPLE_CARDS_EN = [
    {
        "id": "CS2_182",
        "dbfId": 1369,
        "name": "Chillwind Yeti",
        "type": "MINION",
        "cardClass": "NEUTRAL",
        "cost": 4,
        "attack": 4,
        "health": 5,
        "rarity": "FREE",
        "set": "CORE",
        "collectible": True,
        "text": "",
        "mechanics": [],
    },
    {
        "id": "CS2_029",
        "dbfId": 522,
        "name": "Fireball",
        "type": "SPELL",
        "cardClass": "MAGE",
        "cost": 4,
        "rarity": "FREE",
        "set": "CORE",
        "collectible": True,
        "text": "Deal <b>6</b> damage.",
        "mechanics": [],
    },
]


@pytest.mark.asyncio
async def test_fetch_cards_filters_collectible():
    client = HearthstoneJsonClient(base_url="https://fake.api")
    mock_response_ko = AsyncMock()
    mock_response_ko.json.return_value = SAMPLE_CARDS_KO
    mock_response_ko.raise_for_status = lambda: None

    mock_response_en = AsyncMock()
    mock_response_en.json.return_value = SAMPLE_CARDS_EN
    mock_response_en.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.get", side_effect=[mock_response_ko, mock_response_en]):
        cards = await client.fetch_cards()

    # Should filter out non-collectible (ENCHANTMENT without collectible flag)
    assert len(cards) == 2
    assert cards[0]["card_id"] == "CS2_182"
    assert cards[0]["name"] == "Chillwind Yeti"
    assert cards[0]["name_ko"] == "칠풍의 예티"


@pytest.mark.asyncio
async def test_fetch_cards_maps_fields_correctly():
    client = HearthstoneJsonClient(base_url="https://fake.api")
    mock_response_ko = AsyncMock()
    mock_response_ko.json.return_value = [SAMPLE_CARDS_KO[1]]
    mock_response_ko.raise_for_status = lambda: None

    mock_response_en = AsyncMock()
    mock_response_en.json.return_value = [SAMPLE_CARDS_EN[1]]
    mock_response_en.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.get", side_effect=[mock_response_ko, mock_response_en]):
        cards = await client.fetch_cards()

    card = cards[0]
    assert card["card_id"] == "CS2_029"
    assert card["dbf_id"] == 522
    assert card["name"] == "Fireball"
    assert card["name_ko"] == "화염구"
    assert card["card_type"] == "SPELL"
    assert card["hero_class"] == "MAGE"
    assert card["mana_cost"] == 4
    assert card["rarity"] == "FREE"
    assert card["set_name"] == "CORE"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_hearthstone_json.py -v`
Expected: FAIL - ImportError

- [ ] **Step 3: Write implementation**

```python
# src/collector/hearthstone_json.py
from __future__ import annotations

import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)


class HearthstoneJsonClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.HEARTHSTONE_JSON_URL

    async def fetch_cards(self) -> list[dict]:
        """Fetch all collectible cards with Korean + English names."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Fetch Korean cards
            resp_ko = await client.get(f"{self.base_url}/koKR/cards.json")
            resp_ko.raise_for_status()
            raw_ko = resp_ko.json()

            # Fetch English cards
            resp_en = await client.get(f"{self.base_url}/enUS/cards.json")
            resp_en.raise_for_status()
            raw_en = resp_en.json()

        # Build English name lookup
        en_names: dict[str, str] = {}
        for card in raw_en:
            if card.get("collectible"):
                en_names[card["id"]] = card.get("name", "")

        # Filter collectible and map fields
        results: list[dict] = []
        for card in raw_ko:
            if not card.get("collectible"):
                continue

            results.append({
                "card_id": card["id"],
                "dbf_id": card["dbfId"],
                "name": en_names.get(card["id"], card.get("name", "")),
                "name_ko": card.get("name", ""),
                "card_type": card.get("type", ""),
                "hero_class": card.get("cardClass", "NEUTRAL"),
                "mana_cost": card.get("cost", 0),
                "attack": card.get("attack"),
                "health": card.get("health"),
                "durability": card.get("durability"),
                "text": card.get("text", ""),
                "rarity": card.get("rarity", "FREE"),
                "set_name": card.get("set", ""),
                "mechanics": [m for m in card.get("mechanics", [])],
                "collectible": True,
                "json_data": card,
            })

        logger.info("Fetched %d collectible cards from HearthstoneJSON", len(results))
        return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_hearthstone_json.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/collector/hearthstone_json.py tests/test_hearthstone_json.py
git commit -m "feat: add HearthstoneJSON API client with collectible filter"
```

---

### Task 2: Blizzard API client

**Files:**
- Create: `src/collector/blizzard_api.py`
- Create: `tests/test_blizzard_api.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_blizzard_api.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.collector.blizzard_api import BlizzardApiClient


@pytest.mark.asyncio
async def test_get_access_token():
    client = BlizzardApiClient(client_id="test_id", client_secret="test_secret")

    mock_response = AsyncMock()
    mock_response.json.return_value = {"access_token": "test_token", "expires_in": 86399}
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        token = await client._get_access_token()

    assert token == "test_token"


@pytest.mark.asyncio
async def test_fetch_cards_single_page():
    client = BlizzardApiClient(client_id="test_id", client_secret="test_secret")
    client._access_token = "cached_token"

    page1_response = AsyncMock()
    page1_response.json.return_value = {
        "cards": [
            {
                "id": 1369,
                "slug": "1369-chillwind-yeti",
                "name": "Chillwind Yeti",
                "cardTypeId": 4,
                "classId": 12,
                "manaCost": 4,
                "attack": 4,
                "health": 5,
                "rarityId": 1,
                "cardSetId": 1637,
                "collectible": 1,
                "flavorText": "He always wanted to be a Chillwind Abominable.",
            }
        ],
        "pageCount": 1,
        "page": 1,
    }
    page1_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.get", return_value=page1_response):
        cards = await client.fetch_cards()

    assert len(cards) == 1
    assert cards[0]["dbf_id"] == 1369
    assert cards[0]["flavor_text"] == "He always wanted to be a Chillwind Abominable."


@pytest.mark.asyncio
async def test_fetch_cards_retries_on_429():
    client = BlizzardApiClient(client_id="test_id", client_secret="test_secret")
    client._access_token = "cached_token"

    error_response = MagicMock()
    error_response.status_code = 429
    error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "429", request=MagicMock(), response=error_response
    )

    ok_response = AsyncMock()
    ok_response.json.return_value = {"cards": [], "pageCount": 1, "page": 1}
    ok_response.raise_for_status = lambda: None

    import httpx
    with patch("httpx.AsyncClient.get", side_effect=[error_response, ok_response]):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            cards = await client.fetch_cards()

    assert cards == []
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Write implementation**

```python
# src/collector/blizzard_api.py
from __future__ import annotations

import asyncio
import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_BASE = 2.0


class BlizzardApiClient:
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        region: str | None = None,
    ):
        self.client_id = client_id or settings.BLIZZARD_CLIENT_ID
        self.client_secret = client_secret or settings.BLIZZARD_CLIENT_SECRET
        self.region = region or settings.BLIZZARD_API_REGION
        self._access_token: str | None = None

    async def _get_access_token(self) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://oauth.battle.net/token",
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
            )
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            return self._access_token

    async def _request_with_retry(
        self, client: httpx.AsyncClient, url: str, params: dict
    ) -> dict:
        for attempt in range(MAX_RETRIES):
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < MAX_RETRIES - 1:
                    wait = BACKOFF_BASE ** (attempt + 1)
                    logger.warning("Rate limited, retrying in %.1fs...", wait)
                    await asyncio.sleep(wait)
                elif e.response.status_code == 401 and attempt < MAX_RETRIES - 1:
                    logger.warning("Auth failed, refreshing token...")
                    await self._get_access_token()
                    params["access_token"] = self._access_token
                else:
                    raise
        return {}

    async def fetch_cards(self) -> list[dict]:
        if not self._access_token:
            await self._get_access_token()

        base_url = f"https://{self.region}.api.blizzard.com/hearthstone/cards"
        results: list[dict] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "access_token": self._access_token,
                "locale": "en_US",
                "pageSize": 500,
                "page": 1,
                "collectible": "1",
            }

            data = await self._request_with_retry(client, base_url, params)
            page_count = data.get("pageCount", 1)

            for card in data.get("cards", []):
                results.append(self._map_card(card))

            for page in range(2, page_count + 1):
                params["page"] = page
                data = await self._request_with_retry(client, base_url, params)
                for card in data.get("cards", []):
                    results.append(self._map_card(card))

        logger.info("Fetched %d cards from Blizzard API", len(results))
        return results

    @staticmethod
    def _map_card(card: dict) -> dict:
        return {
            "dbf_id": card.get("id"),
            "name": card.get("name", ""),
            "flavor_text": card.get("flavorText", ""),
            "raw_data": card,
        }
```

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add src/collector/blizzard_api.py tests/test_blizzard_api.py
git commit -m "feat: add Blizzard API client with OAuth and retry logic"
```

---

### Task 3: Card sync module

**Files:**
- Create: `src/collector/sync.py`
- Create: `tests/test_sync.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sync.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.tables import Base, Card
from src.collector.sync import sync_cards_to_db


@pytest.fixture
def sync_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


SAMPLE_HS_JSON_CARDS = [
    {
        "card_id": "CS2_182",
        "dbf_id": 1369,
        "name": "Chillwind Yeti",
        "name_ko": "칠풍의 예티",
        "card_type": "MINION",
        "hero_class": "NEUTRAL",
        "mana_cost": 4,
        "attack": 4,
        "health": 5,
        "durability": None,
        "text": "",
        "rarity": "FREE",
        "set_name": "CORE",
        "mechanics": [],
        "collectible": True,
        "json_data": {"id": "CS2_182"},
    },
    {
        "card_id": "CS2_029",
        "dbf_id": 522,
        "name": "Fireball",
        "name_ko": "화염구",
        "card_type": "SPELL",
        "hero_class": "MAGE",
        "mana_cost": 4,
        "attack": None,
        "health": None,
        "durability": None,
        "text": "Deal 6 damage.",
        "rarity": "FREE",
        "set_name": "CORE",
        "mechanics": [],
        "collectible": True,
        "json_data": {"id": "CS2_029"},
    },
]

SAMPLE_BLIZZARD_CARDS = [
    {
        "dbf_id": 1369,
        "name": "Chillwind Yeti",
        "flavor_text": "He always wanted to be a Chillwind Abominable.",
        "raw_data": {},
    },
]


def test_sync_inserts_new_cards(sync_db):
    stats = sync_cards_to_db(sync_db, SAMPLE_HS_JSON_CARDS, [])
    assert stats["inserted"] == 2
    assert stats["updated"] == 0
    assert sync_db.query(Card).count() == 2


def test_sync_updates_existing_cards(sync_db):
    sync_cards_to_db(sync_db, SAMPLE_HS_JSON_CARDS, [])

    updated_cards = [
        {**SAMPLE_HS_JSON_CARDS[0], "mana_cost": 5},
        SAMPLE_HS_JSON_CARDS[1],
    ]
    stats = sync_cards_to_db(sync_db, updated_cards, [])
    assert stats["updated"] == 1
    assert stats["inserted"] == 0

    card = sync_db.query(Card).filter_by(card_id="CS2_182").one()
    assert card.mana_cost == 5


def test_sync_merges_blizzard_flavor_text(sync_db):
    sync_cards_to_db(sync_db, SAMPLE_HS_JSON_CARDS, SAMPLE_BLIZZARD_CARDS)

    card = sync_db.query(Card).filter_by(card_id="CS2_182").one()
    assert card.json_data.get("flavor_text") == "He always wanted to be a Chillwind Abominable."


def test_sync_hearthstone_json_takes_priority(sync_db):
    """HearthstoneJSON data takes priority over Blizzard API data."""
    blizzard_with_different_name = [
        {
            "dbf_id": 1369,
            "name": "Different Name",
            "flavor_text": "Flavor",
            "raw_data": {},
        }
    ]
    sync_cards_to_db(sync_db, SAMPLE_HS_JSON_CARDS, blizzard_with_different_name)

    card = sync_db.query(Card).filter_by(card_id="CS2_182").one()
    assert card.name == "Chillwind Yeti"  # HearthstoneJSON name, not Blizzard
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Write implementation**

```python
# src/collector/sync.py
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.db.tables import Card

logger = logging.getLogger(__name__)


def sync_cards_to_db(
    db: Session,
    hs_json_cards: list[dict],
    blizzard_cards: list[dict],
) -> dict[str, int]:
    """Merge HearthstoneJSON (primary) and Blizzard API (secondary) card data into DB.

    Returns dict with counts: inserted, updated.
    """
    # Build Blizzard lookup by dbf_id
    blizzard_by_dbf: dict[int, dict] = {}
    for bc in blizzard_cards:
        blizzard_by_dbf[bc["dbf_id"]] = bc

    # Build existing card lookup
    existing: dict[str, Card] = {}
    for card in db.query(Card).all():
        existing[card.card_id] = card

    inserted = 0
    updated = 0

    for hc in hs_json_cards:
        card_id = hc["card_id"]
        dbf_id = hc["dbf_id"]

        # Merge Blizzard supplementary data into json_data
        json_data = dict(hc.get("json_data") or {})
        blizzard = blizzard_by_dbf.get(dbf_id, {})
        if blizzard.get("flavor_text"):
            json_data["flavor_text"] = blizzard["flavor_text"]

        if card_id in existing:
            card = existing[card_id]
            changed = False
            for field in (
                "name", "name_ko", "card_type", "hero_class", "mana_cost",
                "attack", "health", "durability", "text", "rarity",
                "set_name", "mechanics", "collectible",
            ):
                new_val = hc.get(field)
                if getattr(card, field) != new_val:
                    setattr(card, field, new_val)
                    changed = True

            if card.json_data != json_data:
                card.json_data = json_data
                changed = True

            if changed:
                card.updated_at = datetime.now(timezone.utc)
                updated += 1
        else:
            card = Card(
                card_id=card_id,
                dbf_id=dbf_id,
                name=hc["name"],
                name_ko=hc["name_ko"],
                card_type=hc["card_type"],
                hero_class=hc["hero_class"],
                mana_cost=hc["mana_cost"],
                attack=hc.get("attack"),
                health=hc.get("health"),
                durability=hc.get("durability"),
                text=hc.get("text", ""),
                rarity=hc["rarity"],
                set_name=hc["set_name"],
                mechanics=hc.get("mechanics", []),
                collectible=hc.get("collectible", True),
                json_data=json_data,
                image_url=f"https://art.hearthstonejson.com/v1/render/latest/koKR/512x/{card_id}.png",
            )
            db.add(card)
            inserted += 1

    db.commit()
    logger.info("Card sync complete: %d inserted, %d updated", inserted, updated)
    return {"inserted": inserted, "updated": updated}
```

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add src/collector/sync.py tests/test_sync.py
git commit -m "feat: add card sync module merging HearthstoneJSON and Blizzard data"
```

---

### Task 4: Image cache module

**Files:**
- Create: `src/collector/image_cache.py`
- Create: `tests/test_image_cache.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_image_cache.py
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from src.collector.image_cache import ImageCacheManager


@pytest.fixture
def tmp_cache_dir(tmp_path):
    return tmp_path / "card_cache"


@pytest.mark.asyncio
async def test_download_card_image(tmp_cache_dir):
    manager = ImageCacheManager(cache_dir=tmp_cache_dir)

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # fake PNG
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        path = await manager.get_card_image("CS2_182")

    assert path.exists()
    assert path.name == "CS2_182.png"


@pytest.mark.asyncio
async def test_cache_hit_skips_download(tmp_cache_dir):
    manager = ImageCacheManager(cache_dir=tmp_cache_dir)

    # Pre-create cached file
    tmp_cache_dir.mkdir(parents=True, exist_ok=True)
    cached = tmp_cache_dir / "CS2_182.png"
    cached.write_bytes(b"cached_image_data")

    with patch("httpx.AsyncClient.get") as mock_get:
        path = await manager.get_card_image("CS2_182")

    mock_get.assert_not_called()
    assert path == cached


@pytest.mark.asyncio
async def test_bulk_download_multiple(tmp_cache_dir):
    manager = ImageCacheManager(cache_dir=tmp_cache_dir)

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.content = b"\x89PNG" + b"\x00" * 50
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        results = await manager.bulk_download(["CS2_182", "CS2_029"])

    assert len(results) == 2
    assert all(p.exists() for p in results.values())


@pytest.mark.asyncio
async def test_download_failure_returns_none(tmp_cache_dir):
    manager = ImageCacheManager(cache_dir=tmp_cache_dir)

    import httpx
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=mock_response
    )

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        path = await manager.get_card_image("NONEXISTENT")

    assert path is None
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Write implementation**

```python
# src/collector/image_cache.py
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import httpx

from config import settings

logger = logging.getLogger(__name__)


class ImageCacheManager:
    def __init__(
        self,
        cache_dir: Path | None = None,
        base_url: str | None = None,
    ):
        self.cache_dir = Path(cache_dir or settings.IMAGE_CACHE_DIR)
        self.base_url = base_url or settings.IMAGE_BASE_URL
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, card_id: str) -> Path:
        return self.cache_dir / f"{card_id}.png"

    async def get_card_image(self, card_id: str) -> Path | None:
        cached = self._cache_path(card_id)
        if cached.exists():
            return cached

        url = f"{self.base_url}/{card_id}.png"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                cached.write_bytes(resp.content)
                return cached
        except httpx.HTTPStatusError:
            logger.warning("Failed to download image for %s", card_id)
            return None
        except httpx.RequestError:
            logger.warning("Network error downloading image for %s", card_id)
            return None

    async def bulk_download(
        self, card_ids: list[str], concurrency: int = 10
    ) -> dict[str, Path]:
        semaphore = asyncio.Semaphore(concurrency)
        results: dict[str, Path] = {}

        async def _download(cid: str):
            async with semaphore:
                path = await self.get_card_image(cid)
                if path:
                    results[cid] = path

        await asyncio.gather(*[_download(cid) for cid in card_ids])
        logger.info("Downloaded %d/%d card images", len(results), len(card_ids))
        return results
```

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add src/collector/image_cache.py tests/test_image_cache.py
git commit -m "feat: add card image cache with bulk download support"
```

---

### Task 5: Wire CLI sync-cards command

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update main.py sync-cards command**

Replace the `sync-cards` handler in main.py:

```python
elif args.command == "sync-cards":
    import asyncio
    from src.db.database import SessionLocal
    from src.collector.hearthstone_json import HearthstoneJsonClient
    from src.collector.blizzard_api import BlizzardApiClient
    from src.collector.sync import sync_cards_to_db
    from src.collector.image_cache import ImageCacheManager

    async def run_sync():
        print("Fetching cards from HearthstoneJSON...")
        hs_client = HearthstoneJsonClient()
        hs_cards = await hs_client.fetch_cards()
        print(f"  Got {len(hs_cards)} collectible cards")

        blizzard_cards = []
        if settings.BLIZZARD_CLIENT_ID:
            print("Fetching cards from Blizzard API...")
            bz_client = BlizzardApiClient()
            blizzard_cards = await bz_client.fetch_cards()
            print(f"  Got {len(blizzard_cards)} cards")
        else:
            print("Blizzard API credentials not set, skipping")

        print("Syncing to database...")
        db = SessionLocal()
        try:
            stats = sync_cards_to_db(db, hs_cards, blizzard_cards)
            print(f"  Inserted: {stats['inserted']}, Updated: {stats['updated']}")

            # Download images
            print("Caching card images...")
            cache = ImageCacheManager()
            card_ids = [c["card_id"] for c in hs_cards]
            downloaded = await cache.bulk_download(card_ids)
            print(f"  Cached {len(downloaded)} images")
        finally:
            db.close()

    asyncio.run(run_sync())
```

- [ ] **Step 2: Verify CLI help still works**

Run: `python main.py sync-cards --help`

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: wire sync-cards CLI command to collector pipeline"
```

---

### Task 6: Run full test suite

- [ ] **Step 1: Run all tests**

Run: `.venv/Scripts/python -m pytest tests/ -v --tb=short`
Expected: All tests pass (previous 30 + new collector tests)

- [ ] **Step 2: Commit if any fixes needed**
