from __future__ import annotations
import random
from src.deckbuilder.recipes import DeckRecipe, SynergyPackage


def detect_synergies(card: dict) -> set[str]:
    """Extract synergy tags from a card dict."""
    tags = set()
    mechs = card.get("mechanics", [])
    if isinstance(mechs, str):
        mechs = [m.strip() for m in mechs.split(",") if m.strip()]
    for m in mechs:
        tags.add(m.upper())

    race = card.get("race", "")
    if race:
        tags.add(race.upper())

    # Also check races list (from CardPoolManager query output)
    for r in card.get("races", []):
        tags.add(r.upper())

    card_type = card.get("card_type", "")
    if card_type:
        tags.add(card_type.upper())

    return tags


def score_card_for_recipe(card: dict, recipe: DeckRecipe,
                          current_deck: list[dict]) -> float:
    """Score a card's fitness for a recipe, including synergy with current deck."""
    cost = max(card.get("mana_cost", 0) or 0, 1)
    attack = card.get("attack", 0) or 0
    health = card.get("health", 0) or 0
    card_type = card.get("card_type", "MINION")

    # Base stat efficiency
    if card_type == "MINION":
        score = (attack + health) / cost
    elif card_type == "SPELL":
        score = 3.0 / cost
    elif card_type == "WEAPON":
        score = (attack + (card.get("durability", 1) or 1)) / cost
    else:
        score = 2.0 / cost

    # Class card bonus
    hero_class = card.get("hero_class", "NEUTRAL")
    if hero_class != "NEUTRAL" and hero_class == recipe.hero_class:
        score += 5.0

    # Synergy with recipe packages
    card_tags = detect_synergies(card)
    for pkg in recipe.packages:
        if pkg.mechanic and pkg.mechanic.upper() in card_tags:
            score += 3.0 * (pkg.priority / 10)
        if pkg.race and pkg.race.upper() in card_tags:
            score += 4.0 * (pkg.priority / 10)
        if pkg.card_type and pkg.card_type.upper() in card_tags:
            score += 1.5 * (pkg.priority / 10)

    # Synergy with cards already in deck
    deck_tags = set()
    for dc in current_deck:
        deck_tags.update(detect_synergies(dc))
    overlap = card_tags & deck_tags
    score += len(overlap) * 0.5

    # Archetype alignment
    arch = recipe.archetype
    if arch in ("aggro", "token", "pirate"):
        score += attack / cost * 1.5  # favor attack
    elif arch in ("control", "big"):
        score += health / cost * 1.0  # favor health
    elif arch == "spell" and card_type == "SPELL":
        score += 2.0

    # Curve fit bonus
    card_cost = card.get("mana_cost", 0) or 0
    cards_at_cost = sum(1 for dc in current_deck if (dc.get("mana_cost", 0) or 0) == card_cost)
    target = recipe.curve.get(min(card_cost, 8), 1)
    if cards_at_cost < target:
        score += 2.0

    # Rarity bonus for legendaries (unique effects)
    if card.get("rarity") == "LEGENDARY":
        score += 1.0

    return score


def build_deck_from_recipe(recipe: DeckRecipe, card_db: dict,
                           deck_size: int = 30) -> dict:
    """Build a deck following a recipe using cards from card_db.

    Returns: {"name": str, "hero": str, "cards": list[str], "archetype": str}
    """
    # Get all valid cards for this class (class cards + neutral), standard only
    available = []
    for cid, card in card_db.items():
        # Only collectible standard cards
        if not card.get("collectible", True):
            continue
        hero_class = card.get("hero_class", "NEUTRAL")
        if hero_class not in (recipe.hero_class, "NEUTRAL"):
            continue
        # Skip hero types for now
        if card.get("card_type") in ("HERO",):
            continue
        available.append(card)

    deck: list[dict] = []  # cards selected so far
    deck_ids: list[str] = []  # card_ids (with duplicates)
    used_count: dict[str, int] = {}  # card_id -> copies used

    def can_add(card: dict) -> bool:
        cid = card["card_id"]
        max_copies = 1 if card.get("rarity") == "LEGENDARY" else 2
        return used_count.get(cid, 0) < max_copies

    def add_card(card: dict):
        cid = card["card_id"]
        deck.append(card)
        deck_ids.append(cid)
        used_count[cid] = used_count.get(cid, 0) + 1

    # Phase 1: Fill synergy packages (by priority)
    sorted_pkgs = sorted(recipe.packages, key=lambda p: -p.priority)
    for pkg in sorted_pkgs:
        # Filter cards matching this package
        pkg_cards = []
        for card in available:
            if not can_add(card):
                continue
            tags = detect_synergies(card)
            match = False
            if pkg.mechanic and pkg.mechanic.upper() in tags:
                match = True
            if pkg.race and pkg.race.upper() in tags:
                match = True
            if pkg.card_type and pkg.card_type.upper() == card.get("card_type", "").upper():
                match = True
            if match:
                pkg_cards.append(card)

        # Score and sort
        pkg_cards.sort(key=lambda c: score_card_for_recipe(c, recipe, deck), reverse=True)

        added = 0
        for card in pkg_cards:
            if added >= pkg.max_cards:
                break
            if len(deck_ids) >= deck_size:
                break
            if not can_add(card):
                continue
            add_card(card)
            added += 1
            # Add second copy if non-legendary and still need cards
            if can_add(card) and added < pkg.max_cards and len(deck_ids) < deck_size:
                add_card(card)
                added += 1

    # Phase 2: Fill remaining by curve
    remaining = deck_size - len(deck_ids)
    if remaining > 0:
        # Score all remaining available cards
        fillers = [c for c in available if can_add(c)]
        fillers.sort(key=lambda c: score_card_for_recipe(c, recipe, deck), reverse=True)

        for card in fillers:
            if len(deck_ids) >= deck_size:
                break
            if not can_add(card):
                continue
            add_card(card)
            if can_add(card) and len(deck_ids) < deck_size:
                add_card(card)

    # Phase 3: If still short, pad with random available
    while len(deck_ids) < deck_size and available:
        card = random.choice(available)
        if can_add(card):
            add_card(card)

    return {
        "name": recipe.name,
        "hero": recipe.hero_class,
        "cards": deck_ids[:deck_size],
        "archetype": recipe.archetype,
    }
