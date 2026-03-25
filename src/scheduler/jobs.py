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

        blizzard_cards = []
        if settings.BLIZZARD_CLIENT_ID:
            from src.collector.blizzard_api import BlizzardApiClient
            bz_client = BlizzardApiClient()
            blizzard_cards = await bz_client.fetch_cards()
            logger.info("Fetched %d cards from Blizzard API", len(blizzard_cards))

        db = SessionLocal()
        try:
            stats = sync_cards_to_db(db, hs_cards, blizzard_cards)
            logger.info("Sync complete: inserted=%d, updated=%d",
                        stats["inserted"], stats["updated"])
        finally:
            db.close()

    asyncio.run(_sync())


def create_scheduler() -> BlockingScheduler:
    """Create and configure the daily scheduler."""
    scheduler = BlockingScheduler()

    trigger = CronTrigger(
        hour=settings.SCHEDULER_CRON_HOUR,
        minute=settings.SCHEDULER_CRON_MINUTE,
    )

    scheduler.add_job(job_sync_cards, trigger, id="sync_cards", name="Sync card data")

    return scheduler
