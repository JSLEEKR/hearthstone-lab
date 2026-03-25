import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="Hearthstone Lab")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("serve", help="Start web dashboard")

    sync_parser = subparsers.add_parser("sync-cards", help="Sync card data")
    sync_parser.add_argument("--update-standard", action="store_true",
                             help="Update standard format flags")

    sim_parser = subparsers.add_parser("simulate", help="Run simulations")
    sim_parser.add_argument("--bulk", action="store_true",
                            help="Run bulk simulation for all meta decks")

    tournament_parser = subparsers.add_parser("tournament", help="Run round-robin tournament")
    tournament_parser.add_argument("--matches", type=int, default=50, help="Matches per pair")
    tournament_parser.add_argument("--ai", choices=["rule", "score", "mcts"], default="rule", help="AI level")

    subparsers.add_parser("scheduler", help="Start daily scheduler")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "serve":
        import uvicorn
        from config import settings
        uvicorn.run("src.web.app:app", host=settings.WEB_HOST, port=settings.WEB_PORT, reload=True)
    elif args.command == "sync-cards":
        import asyncio
        from config import settings
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

                print("Caching card images...")
                cache = ImageCacheManager()
                card_ids = [c["card_id"] for c in hs_cards]
                downloaded = await cache.bulk_download(card_ids)
                print(f"  Cached {len(downloaded)} images")
            finally:
                db.close()

        asyncio.run(run_sync())
    elif args.command == "simulate":
        from src.simulator.match import run_match, MatchResult

        # Demo: run a simple test match
        card_db = {
            f"card_{i}": {
                "card_id": f"card_{i}", "card_type": "MINION",
                "mana_cost": (i % 8) + 1, "attack": (i % 5) + 1,
                "health": (i % 5) + 1, "mechanics": [], "name": f"Card {i}",
            }
            for i in range(30)
        }
        deck = [f"card_{i}" for i in range(15)] * 2

        if args.bulk:
            print("Running bulk simulation (10 matches)...")
            wins = {"A": 0, "B": 0, "draw": 0}
            for i in range(10):
                result = run_match(deck_a=list(deck), deck_b=list(deck),
                                   hero_a="MAGE", hero_b="WARRIOR",
                                   card_db=card_db, max_turns=60)
                if result.winner == "A":
                    wins["A"] += 1
                elif result.winner == "B":
                    wins["B"] += 1
                else:
                    wins["draw"] += 1
            print(f"Results: {wins}")
        else:
            print("Running single match...")
            result = run_match(deck_a=list(deck), deck_b=list(deck),
                               hero_a="MAGE", hero_b="WARRIOR",
                               card_db=card_db, max_turns=60)
            print(f"Winner: {result.winner or 'Draw'}, Turns: {result.turns}")
    elif args.command == "tournament":
        from src.db.database import SessionLocal
        from src.db.tables import Deck, DeckCard, Card
        from src.simulator.tournament import Tournament
        from src.simulator.ai import RuleBasedAI, ScoreBasedAI, MCTSAI

        ai_map = {"rule": RuleBasedAI, "score": ScoreBasedAI, "mcts": MCTSAI(iterations=50)}
        ai_class = ai_map.get(args.ai, RuleBasedAI)

        db = SessionLocal()
        try:
            all_decks = db.query(Deck).all()
            if len(all_decks) < 2:
                print("Need at least 2 decks in database. Create decks first.")
                sys.exit(1)

            print(f"Available decks ({len(all_decks)}):")
            for d in all_decks:
                print(f"  [{d.id}] {d.name} ({d.hero_class})")

            decks_data = {}
            combined_card_db = {}
            for deck in all_decks:
                rows = (
                    db.query(DeckCard, Card)
                    .join(Card, DeckCard.card_id == Card.id)
                    .filter(DeckCard.deck_id == deck.id).all()
                )
                if not rows:
                    continue
                deck_list = []
                for dc, card in rows:
                    combined_card_db[card.card_id] = {
                        "card_id": card.card_id, "card_type": card.card_type,
                        "mana_cost": card.mana_cost, "attack": card.attack or 0,
                        "health": card.health or 0, "mechanics": card.mechanics or [],
                        "name": card.name, "text": card.text or "",
                    }
                    for _ in range(dc.count):
                        deck_list.append(card.card_id)
                if len(deck_list) >= 10:
                    decks_data[deck.name] = {"hero": deck.hero_class, "cards": deck_list}

            if len(decks_data) < 2:
                print("Need at least 2 decks with cards. Build decks first.")
                sys.exit(1)

            print(f"\nRunning tournament with {len(decks_data)} decks, {args.matches} matches/pair, AI={args.ai}...")
            t = Tournament(decks_data, combined_card_db,
                           matches_per_pair=args.matches, ai_class=ai_class)
            result = t.run()
            print(result.summary())
        finally:
            db.close()
    elif args.command == "scheduler":
        from src.scheduler.jobs import create_scheduler
        from config import settings
        print("Starting scheduler (daily jobs at {:02d}:{:02d})...".format(
            settings.SCHEDULER_CRON_HOUR, settings.SCHEDULER_CRON_MINUTE))
        sched = create_scheduler()
        try:
            sched.start()
        except KeyboardInterrupt:
            print("Scheduler stopped.")


if __name__ == "__main__":
    main()
