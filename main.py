import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="Hearthstone Deck Maker")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("serve", help="Start web dashboard")

    sync_parser = subparsers.add_parser("sync-cards", help="Sync card data")
    sync_parser.add_argument("--update-standard", action="store_true",
                             help="Update standard format flags")

    sim_parser = subparsers.add_parser("simulate", help="Run simulations")
    sim_parser.add_argument("--bulk", action="store_true",
                            help="Run bulk simulation for all meta decks")

    subparsers.add_parser("update-tierlist", help="Recalculate tier list")

    subparsers.add_parser("scheduler", help="Start daily scheduler")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "serve":
        print("Web server not yet implemented (sub-project 6)")
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
                                   card_db=card_db, max_turns=45)
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
                               card_db=card_db, max_turns=45)
            print(f"Winner: {result.winner or 'Draw'}, Turns: {result.turns}")
    elif args.command == "update-tierlist":
        print("Tier list not yet implemented (sub-project 5)")
    elif args.command == "scheduler":
        print("Scheduler not yet implemented (sub-project 6)")


if __name__ == "__main__":
    main()
