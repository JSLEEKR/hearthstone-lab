<div align="center">

# ⚔️ Hearthstone Lab

### Build decks. Run simulations. Test strategies.

[![GitHub Stars](https://img.shields.io/github/stars/JSLEEKR/hearthstone-lab?style=for-the-badge&logo=github&color=yellow)](https://github.com/JSLEEKR/hearthstone-lab/stargazers)
[![Python](https://img.shields.io/badge/python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Claude](https://img.shields.io/badge/built%20with-Claude%20Code-D4A574?style=for-the-badge)](https://claude.ai)

<br/>

**A deck-building and game simulation laboratory for Hearthstone**

Full game engine · 7,800+ cards · AI opponents · Dark-themed web UI

[🃏 Card Database](#-card-database) · [🔨 Deck Builder](#-deck-builder) · [⚔️ Simulator](#️-game-simulator) · [🚀 Quick Start](#-quick-start)

</div>

---

## Why This Exists

Building a Hearthstone deck is part theory, part gut feeling. You pick 30 cards, queue up, and hope for the best. But what if you could **test your deck before playing it?**

**Hearthstone Lab** lets you build decks and run AI-powered simulations to see how they actually perform. It implements the full Hearthstone game engine — mana, combat, keywords, hero powers — so you can pit any two decks against each other and get real win rate data.

No more guessing. Build. Simulate. Iterate.

---

## ✨ Features

### 🃏 Card Database

| Feature | Description |
|---------|-------------|
| **7,800+ cards** | Every collectible card with English & Korean names |
| **Smart filters** | Class, mana cost, rarity, card type, expansion, format |
| **Card detail modal** | Full stats, effects, and mechanics breakdown |
| **Format toggle** | Standard / Wild / All |

### 🔨 Deck Builder

| Feature | Description |
|---------|-------------|
| **3-column UI** | Filters \| Card grid \| Deck list — all on one screen |
| **Rule validation** | 30-card limit, 2x copies, legendary limit enforced |
| **AI deck generation** | Auto-build optimized decks by archetype |
| **Deckstring support** | Import/export compatible with Hearthstone client |
| **Mana curve** | Real-time mana curve visualization |

### ⚔️ Game Simulator

| Category | Supported Mechanics |
|----------|-------------------|
| **Combat** | Taunt, Divine Shield, Rush, Windfury, Stealth, Freeze, Poisonous, Lifesteal, Reborn, Enrage |
| **Keywords** | Battlecry, Deathrattle, Combo, Echo, Tradeable, Miniaturize, Spell Power, Secrets |
| **Advanced** | Outcast, Frenzy, Spellburst, Aura, Silence, Elusive, Overload |
| **Hero Powers** | All 10 classes fully implemented |
| **AI** | Greedy AI + Monte Carlo Tree Search (MCTS) |

### 🖥️ Web Dashboard

- Hearthstone-themed dark UI with stone/wood aesthetic
- Built with **HTMX + Alpine.js** for snappy, SPA-like interactions
- Pages: Card DB, Deck Builder, Simulation

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Web | FastAPI + Jinja2 |
| Database | SQLAlchemy (SQLite default, PostgreSQL ready) |
| Migrations | Alembic |
| Frontend | HTMX + Alpine.js + Chart.js |
| Scheduler | APScheduler |
| Testing | pytest |

---

## 📁 Project Structure

```
hearthstone-lab/
├── src/
│   ├── collector/        # Card data sync (HearthstoneJSON, Blizzard API)
│   ├── core/             # Game models, enums, deckstring codec, rules
│   ├── db/               # Database session & ORM models
│   ├── deckbuilder/      # Manual & auto deck builder, archetype classifier
│   ├── simulator/        # Game engine, AI, spell parser, event log
│   ├── scheduler/        # Background jobs (daily card sync)
│   └── web/              # FastAPI app, routes, templates, static assets
├── tests/                # Test suite
├── config.py             # App configuration
├── main.py               # CLI entry point
└── requirements.txt      # Dependencies
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+

### Setup

```bash
git clone https://github.com/JSLEEKR/hearthstone-lab.git
cd hearthstone-lab
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Initialize & Sync

```bash
# Create database
alembic upgrade head

# Fetch 7,800+ cards from HearthstoneJSON API
python main.py sync-cards
```

### Run

```bash
# Start web dashboard → http://127.0.0.1:8000
python main.py serve

# Run a single simulation
python main.py simulate

# Bulk simulation (10 matches)
python main.py simulate --bulk

# Daily card sync scheduler
python main.py scheduler
```

### Test

```bash
pytest -v --cov=src tests/
```

---

## ⚙️ Configuration

Create a `.env` file (optional):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///hearthstone.db` | Database connection |
| `BLIZZARD_CLIENT_ID` | — | Blizzard API client ID |
| `BLIZZARD_CLIENT_SECRET` | — | Blizzard API secret |
| `BLIZZARD_API_REGION` | `kr` | API region |
| `SIM_MATCHES_PER_MATCHUP` | `100` | Simulations per matchup |
| `SIM_MAX_TURNS` | `45` | Max turns per game |
| `MCTS_ITERATIONS` | `1000` | MCTS search iterations |

---

## 📊 Data Sources

| Source | Usage | License |
|--------|-------|---------|
| [HearthstoneJSON](https://hearthstonejson.com/) | Card data (names, stats, mechanics) | Free / CC0 |
| [Blizzard Game Data API](https://develop.battle.net/) | Official card data & flavor text | Blizzard ToS |

---

<div align="center">

### Built with ⚔️ and [Claude Code](https://claude.ai/claude-code)

Hearthstone is a registered trademark of Blizzard Entertainment.

</div>
