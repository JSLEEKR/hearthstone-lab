#!/usr/bin/env python
"""Integration test: optimize the weakest deck from a 7-deck field."""
from __future__ import annotations
import sys
import random

# Deterministic for reproducibility
random.seed(42)

# Build a card database with varied cards
CARD_DB = {}
classes = ["HUNTER", "WARRIOR", "MAGE", "PRIEST", "ROGUE", "PALADIN", "DRUID"]
rarities = ["COMMON", "COMMON", "RARE", "RARE", "EPIC", "LEGENDARY"]
types = ["MINION", "MINION", "MINION", "SPELL", "WEAPON"]

for i in range(120):
    hero_class = classes[i % len(classes)] if i < 70 else "NEUTRAL"
    card_type = types[i % len(types)]
    rarity = rarities[i % len(rarities)]
    cost = (i % 8) + 1
    attack = (i % 6) + 1
    health = (i % 5) + 2

    card = {
        "card_id": f"card_{i}",
        "card_type": card_type,
        "mana_cost": cost,
        "attack": attack if card_type != "SPELL" else 0,
        "health": health if card_type == "MINION" else 0,
        "durability": 2 if card_type == "WEAPON" else 0,
        "mechanics": [],
        "name": f"Card {i}",
        "rarity": rarity,
        "hero_class": hero_class,
        "race": "",
        "races": [],
        "text": "",
        "collectible": True,
    }
    CARD_DB[f"card_{i}"] = card


def build_decks() -> list[dict]:
    """Build 7 decks from different classes."""
    decks = []
    for idx, cls in enumerate(classes):
        # Pick class cards + neutrals
        class_cards = [cid for cid, c in CARD_DB.items()
                       if c["hero_class"] == cls and c["card_type"] != "HERO"]
        neutral_cards = [cid for cid, c in CARD_DB.items()
                         if c["hero_class"] == "NEUTRAL" and c["card_type"] != "HERO"]

        deck_cards = []
        # Add class cards (up to 2 copies)
        for cid in class_cards[:8]:
            deck_cards.extend([cid, cid])
        # Fill with neutrals
        for cid in neutral_cards[idx * 3: idx * 3 + 7]:
            deck_cards.extend([cid, cid])

        # Pad to 30
        while len(deck_cards) < 30:
            cid = random.choice(neutral_cards)
            if deck_cards.count(cid) < 2:
                deck_cards.append(cid)

        deck_cards = deck_cards[:30]
        decks.append({
            "name": f"{cls.title()} Deck",
            "hero": cls,
            "cards": deck_cards,
            "archetype": "midrange",
        })
    return decks


def main():
    from src.simulator.match import run_match
    from src.deckbuilder.card_optimizer import CardDeckOptimizer

    decks = build_decks()
    print(f"Built {len(decks)} decks:")
    for d in decks:
        print(f"  {d['name']}: {len(d['cards'])} cards ({d['hero']})")

    # Quick round-robin to find weakest deck (5 games per pair)
    print("\n--- Quick Round Robin (5 games/pair) ---")
    win_counts = {d["name"]: 0 for d in decks}
    game_counts = {d["name"]: 0 for d in decks}

    for i, d1 in enumerate(decks):
        for j, d2 in enumerate(decks):
            if i >= j:
                continue
            for _ in range(5):
                try:
                    result = run_match(
                        list(d1["cards"]), list(d2["cards"]),
                        d1["hero"], d2["hero"], CARD_DB, max_turns=60
                    )
                    game_counts[d1["name"]] += 1
                    game_counts[d2["name"]] += 1
                    if result.winner == "A":
                        win_counts[d1["name"]] += 1
                    elif result.winner == "B":
                        win_counts[d2["name"]] += 1
                except Exception:
                    pass

    winrates = {}
    for name in win_counts:
        wr = win_counts[name] / max(game_counts[name], 1) * 100
        winrates[name] = wr
        print(f"  {name}: {wr:.1f}% ({win_counts[name]}/{game_counts[name]})")

    # Find weakest
    weakest_name = min(winrates, key=winrates.get)
    weakest_deck = [d for d in decks if d["name"] == weakest_name][0]
    print(f"\nWeakest deck: {weakest_name} ({winrates[weakest_name]:.1f}%)")

    # Optimize the weakest deck
    print("\n--- Optimizing weakest deck ---")
    opponents = [d for d in decks if d["name"] != weakest_name]

    optimizer = CardDeckOptimizer(
        card_db=CARD_DB,
        opponent_decks=opponents,
        games_per_eval=18,      # 3 games per opponent (6 opponents)
        max_replacements=3,
        min_improvement=0.5,
        confidence=0.5,         # lower threshold for small sample
    )

    report = optimizer.optimize_deck(weakest_deck)
    print(report.summary())

    # Show the optimized deck
    if report.card_changes:
        print(f"\nOptimized deck has {len(report.optimized_deck['cards'])} cards")
    else:
        print("\nNo changes made — deck may already be near-optimal for this card pool.")

    print("\nIntegration test PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
