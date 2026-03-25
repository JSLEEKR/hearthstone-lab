from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import settings

logger = logging.getLogger(__name__)


def job_sync_cards():
    """Daily card data sync from HearthstoneJSON + Blizzard API."""
    import asyncio
    from src.db.database import SessionLocal
    from src.collector.hearthstone_json import HearthstoneJsonClient
    from src.collector.sync import sync_cards_to_db

    async def _sync():
        logger.info("Starting card sync...")
        hs_client = HearthstoneJsonClient()
        hs_cards = await hs_client.fetch_cards()
        logger.info("Fetched %d cards from HearthstoneJSON", len(hs_cards))

        db = SessionLocal()
        try:
            stats = sync_cards_to_db(db, hs_cards, [])
            logger.info("Sync complete: inserted=%d, updated=%d",
                        stats["inserted"], stats["updated"])
        finally:
            db.close()

    asyncio.run(_sync())


def job_scrape_hsreplay():
    """Daily HSReplay data collection."""
    import asyncio
    from src.db.database import SessionLocal
    from src.scraper.api_client import HSReplayClient
    from src.scraper.parser import HSReplayParser

    async def _scrape():
        logger.info("Starting HSReplay scrape...")
        client = HSReplayClient()

        db = SessionLocal()
        try:
            parser = HSReplayParser(db)
            total_saved = 0
            for fmt in ["standard", "wild"]:
                raw_data = await client.fetch_deck_stats(format_type=fmt)
                logger.info("Fetched %d deck stats from HSReplay (%s)", len(raw_data), fmt)
                parsed = parser.parse_deck_stats(raw_data, format_type=fmt)
                for entry in parsed:
                    deck = parser.find_or_create_deck(
                        hero_class=entry["hero_class"],
                        format_type=entry["format"],
                        deckstring=entry.get("deckstring"),
                    )
                    parser.save_stats(
                        deck.id,
                        winrate=entry["winrate"],
                        playrate=entry["playrate"],
                        games_played=entry["games_played"],
                    )
                total_saved += len(parsed)
            logger.info("Saved %d total deck stats", total_saved)
        finally:
            db.close()

    asyncio.run(_scrape())


def job_update_tierlist():
    """Daily tier list recalculation."""
    from src.db.database import SessionLocal
    from src.tierlist.calculator import TierCalculator
    from src.tierlist.ranker import TierRanker
    from src.tierlist.history import TierHistoryTracker

    logger.info("Updating tier list...")
    db = SessionLocal()
    try:
        calc = TierCalculator(
            weight_sim=settings.TIER_WEIGHT_SIM,
            weight_hsreplay=settings.TIER_WEIGHT_HSREPLAY,
        )
        ranker = TierRanker()
        tracker = TierHistoryTracker(db)

        for fmt in ["standard", "wild"]:
            deck_winrates = calc.get_deck_winrates(db, format_type=fmt)
            ranked = ranker.rank_decks(deck_winrates)
            for entry in ranked:
                tracker.record(
                    deck_id=entry["deck_id"],
                    tier=entry["tier"],
                    sim_winrate=entry.get("sim_winrate"),
                    hsreplay_winrate=entry.get("hsreplay_winrate"),
                    combined_winrate=entry["combined_winrate"],
                )
            logger.info("Updated %d decks for %s", len(ranked), fmt)
    finally:
        db.close()


def create_scheduler() -> BlockingScheduler:
    """Create and configure the daily scheduler."""
    scheduler = BlockingScheduler()

    trigger = CronTrigger(
        hour=settings.SCHEDULER_CRON_HOUR,
        minute=settings.SCHEDULER_CRON_MINUTE,
    )

    scheduler.add_job(job_sync_cards, trigger, id="sync_cards", name="Sync card data")
    scheduler.add_job(job_scrape_hsreplay, trigger, id="scrape_hsreplay",
                      name="Scrape HSReplay data",
                      misfire_grace_time=3600)
    scheduler.add_job(job_update_tierlist, trigger, id="update_tierlist",
                      name="Update tier list",
                      misfire_grace_time=3600)

    return scheduler
