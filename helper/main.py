"""Hearthstone Game Helper — main entry point."""
from __future__ import annotations
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def build_card_db():
    """Load card database."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from src.db.database import SessionLocal
        from src.db.tables import Card

        db = SessionLocal()
        cards = db.query(Card).filter(Card.collectible == True).all()  # noqa: E712
        card_db = {}
        for c in cards:
            mechs = c.mechanics or []
            if isinstance(mechs, str):
                mechs = [m.strip() for m in mechs.split(",") if m.strip()]
            card_db[c.card_id] = {
                "card_id": c.card_id, "name": c.name or "",
                "card_type": c.card_type or "MINION",
                "mana_cost": c.mana_cost or 0,
                "attack": c.attack or 0, "health": c.health or 0,
                "mechanics": mechs, "text": c.text or "",
                "rarity": c.rarity or "",
            }
        db.close()
        logger.info(f"Loaded {len(card_db)} cards from DB")
        return card_db
    except Exception as e:
        logger.warning(f"Could not load card DB: {e}")
        return {}


def main():
    from helper.log_watcher import LogWatcher, ensure_log_config, find_power_log
    from helper.game_tracker import GameTracker
    from helper.advisor import GameAdvisor
    from helper.overlay import OverlayWindow

    # Step 1: Ensure log.config exists
    created = ensure_log_config()
    if created:
        logger.info("Created log.config — restart Hearthstone to enable logging")

    # Step 2: Find Power.log
    log_path = find_power_log()
    if not log_path:
        logger.warning("Power.log not found. Starting in demo mode.")

    # Step 3: Load card database
    card_db = build_card_db()

    # Step 4: Initialize components
    watcher = LogWatcher(log_path)
    tracker = GameTracker(card_db)
    advisor = GameAdvisor(card_db)
    overlay = OverlayWindow()

    # Step 5: Start log watcher
    if log_path:
        watcher.start()
        overlay.update_status(f"Watching: {log_path.name}")
    else:
        overlay.update_status("Demo mode — no Power.log found")

    # Step 6: Update loop
    def update():
        # Process new events
        events = watcher.get_events()
        for event in events:
            tracker.process_event(event)

        state = tracker.state

        if state.in_game:
            # Update overlay
            stats = advisor.get_deck_stats(state)
            overlay.update_stats(stats)

            recs = advisor.get_recommendations(state)
            overlay.update_recommendations(recs)

            overlay.update_opponent(state)
            overlay.update_events(state.events_log)

            opp_type = advisor.get_opponent_profile(state)
            overlay.update_status(f"In Game — Turn {state.turn} | Opp: {opp_type}")
        else:
            overlay.update_status("Waiting for game..." if log_path else "Demo mode")

        overlay.schedule(200, update)  # Update every 200ms

    overlay.schedule(200, update)

    logger.info("Helper started! Overlay is visible.")
    logger.info("Right-click + drag to move the overlay.")
    logger.info("Close the overlay window to exit.")

    overlay.run()


if __name__ == "__main__":
    main()
