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
        print("Card sync not yet implemented (sub-project 2)")
    elif args.command == "simulate":
        print("Simulation not yet implemented (sub-project 3)")
    elif args.command == "update-tierlist":
        print("Tier list not yet implemented (sub-project 5)")
    elif args.command == "scheduler":
        print("Scheduler not yet implemented (sub-project 6)")


if __name__ == "__main__":
    main()
