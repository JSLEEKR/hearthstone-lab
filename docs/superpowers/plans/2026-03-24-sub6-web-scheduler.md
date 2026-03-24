# Sub-Project 6: Web Dashboard + Scheduler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build FastAPI + Jinja2 + HTMX web dashboard (tier list, deck builder, card gallery, simulation) and APScheduler daily batch jobs.

**Architecture:** `src/web/` contains FastAPI app, routes, templates. `src/scheduler/` contains APScheduler jobs. `main.py` wires CLI commands.

**Tech Stack:** FastAPI, Jinja2, HTMX, Alpine.js, Chart.js, APScheduler, uvicorn

---

## File Structure

```
src/web/
├── __init__.py
├── app.py              # FastAPI app factory
├── routes/
│   ├── __init__.py
│   ├── pages.py        # HTML page routes
│   └── api.py          # HTMX/JSON API routes
├── templates/
│   ├── base.html       # Layout with navbar, HTMX/Alpine.js
│   ├── tierlist.html   # Tier list page (/)
│   ├── cards.html      # Card gallery (/cards)
│   ├── builder.html    # Deck builder (/builder)
│   ├── deck.html       # Deck detail (/deck/{id})
│   └── simulation.html # Simulation (/simulation)
├── static/
│   ├── css/
│   │   └── style.css
│   └── card_cache/
│       └── .gitkeep

src/scheduler/
├── __init__.py
└── jobs.py             # APScheduler job definitions

tests/
├── test_web.py
└── test_scheduler.py
```

---

### Task 1: FastAPI app + base templates + static CSS

**Files:**
- Create: `src/web/app.py`
- Create: `src/web/routes/__init__.py`
- Create: `src/web/routes/pages.py`
- Create: `src/web/templates/base.html`
- Create: `src/web/static/css/style.css`
- Create: `tests/test_web.py` (basic app tests)

### Task 2: API routes (cards, deck CRUD, tierlist, simulation)

**Files:**
- Create: `src/web/routes/api.py`
- Extend: `tests/test_web.py`

### Task 3: Page templates (tierlist, cards, builder, deck detail, simulation)

**Files:**
- Create: `src/web/templates/tierlist.html`
- Create: `src/web/templates/cards.html`
- Create: `src/web/templates/builder.html`
- Create: `src/web/templates/deck.html`
- Create: `src/web/templates/simulation.html`

### Task 4: Scheduler + main.py wiring

**Files:**
- Create: `src/scheduler/jobs.py`
- Modify: `main.py` (wire serve + scheduler commands)
- Create: `tests/test_scheduler.py`
