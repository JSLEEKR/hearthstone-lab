# Hearthstone Lab

A deck-building and simulation laboratory for Hearthstone. Build decks, run AI-powered simulations, and test strategies — all in one place.

## Features

### Game Simulator
- Full Hearthstone game engine with mana, hand, board, and deck mechanics
- **Combat:** Taunt, Divine Shield, Rush, Windfury, Stealth, Freeze, Poisonous, Lifesteal, Reborn, Enrage
- **Keywords:** Battlecry, Deathrattle, Combo, Echo, Tradeable, Miniaturize, Spell Power, Secrets, Outcast, Frenzy, Spellburst, Aura, Silence
- **Hero Powers:** All 10 classes supported
- AI opponents (Greedy AI / MCTS)
- Event logging & step-through debug mode

### Deck Builder
- Manual deck construction with full rule validation (30 cards, 2x copy limit, legendary limit)
- AI-powered auto deck generation with mana curve optimization
- Deckstring import/export (compatible with Hearthstone client)
- Interactive 3-column UI: filters | card grid | deck list

### Card Database
- 7,800+ collectible cards with Korean & English names
- Filter by class, mana cost, rarity, card type, expansion, and format
- Card detail modal with stats, effects, and mechanics
- Standard/Wild format toggle

### Web Dashboard
- Clean Hearthstone-themed dark UI
- Pages: Card DB, Deck Builder, Simulation
- Built with HTMX + Alpine.js for snappy interactions

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Web | FastAPI + Jinja2 |
| Database | SQLAlchemy (SQLite default, PostgreSQL ready) |
| Migrations | Alembic |
| Frontend | HTMX + Alpine.js + Chart.js |
| Scheduler | APScheduler |
| Testing | pytest |

## Project Structure

```
src/
├── collector/        # Card data sync (HearthstoneJSON API, Blizzard API)
├── core/             # Game models, enums, deckstring codec, rules
├── db/               # Database session & ORM models
├── deckbuilder/      # Manual & auto deck builder, archetype classifier
├── simulator/        # Game engine, AI, spell parser, event log
├── scheduler/        # Background jobs (daily card sync)
└── web/              # FastAPI app, routes, templates, static assets
```

## Getting Started

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
git clone https://github.com/JSLEEKR/hearthstone-lab.git
cd hearthstone-lab
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Setup

```bash
cp .env.example .env
# Optional: add Blizzard API credentials for extended card data
```

### Initialize Database

```bash
alembic upgrade head
```

### Sync Card Data

```bash
python main.py sync-cards
```

### Run

```bash
# Start web dashboard (http://127.0.0.1:8000)
python main.py serve

# Run simulations
python main.py simulate          # Single match
python main.py simulate --bulk   # Bulk matches (10)

# Start background scheduler (daily card sync)
python main.py scheduler
```

### Run Tests

```bash
pytest -v --cov=src tests/
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///hearthstone.db` | Database connection string |
| `BLIZZARD_CLIENT_ID` | — | Blizzard API client ID (optional) |
| `BLIZZARD_CLIENT_SECRET` | — | Blizzard API secret (optional) |
| `BLIZZARD_API_REGION` | `kr` | Blizzard API region |
| `SIM_MATCHES_PER_MATCHUP` | `100` | Simulations per matchup |
| `SIM_MAX_TURNS` | `45` | Max turns per game |
| `MCTS_ITERATIONS` | `1000` | MCTS search iterations |

## Data Sources

- [HearthstoneJSON](https://hearthstonejson.com/) — Free card data API
- [Blizzard Game Data API](https://develop.battle.net/) — Official Hearthstone API

## License

This project is for personal learning and experimentation.
Hearthstone is a registered trademark of Blizzard Entertainment.
