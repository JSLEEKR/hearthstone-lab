from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.tables import Card, Deck, DeckCard

router = APIRouter()


@router.get("/cards")
def search_cards(
    db: Session = Depends(get_db),
    q: str = "",
    hero_class: str = "",
    cost: int | None = None,
    rarity: str = "",
    set_name: str = "",
    page: int = 1,
    per_page: int = 20,
):
    query = db.query(Card).filter(Card.collectible == True)
    if q:
        query = query.filter(Card.name.ilike(f"%{q}%") | Card.name_ko.ilike(f"%{q}%"))
    if hero_class:
        query = query.filter(Card.hero_class.in_([hero_class, "NEUTRAL"]))
    if cost is not None:
        query = query.filter(Card.mana_cost == cost)
    if rarity:
        query = query.filter(Card.rarity == rarity)
    if set_name:
        query = query.filter(Card.set_name == set_name)

    total = query.count()
    cards = query.order_by(Card.mana_cost, Card.name).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "cards": [
            {
                "id": c.id, "card_id": c.card_id, "name": c.name,
                "name_ko": c.name_ko, "mana_cost": c.mana_cost,
                "attack": c.attack, "health": c.health,
                "card_type": c.card_type, "rarity": c.rarity,
                "hero_class": c.hero_class, "set_name": c.set_name,
                "text": c.text, "image_url": c.image_url,
            }
            for c in cards
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("/deck/create")
def create_deck(
    name: str, hero_class: str, format: str = "standard",
    db: Session = Depends(get_db),
):
    deck = Deck(name=name, hero_class=hero_class, format=format, source="manual")
    db.add(deck)
    db.commit()
    return {"deck_id": deck.id, "name": deck.name}


@router.post("/deck/add-card")
def add_card_to_deck(
    deck_id: int, card_id: str, db: Session = Depends(get_db),
):
    card = db.query(Card).filter_by(card_id=card_id).first()
    if not card:
        return {"success": False, "error": "Card not found"}

    existing = db.query(DeckCard).filter_by(deck_id=deck_id, card_id=card.id).first()
    if existing:
        max_count = 1 if card.rarity == "LEGENDARY" else 2
        if existing.count >= max_count:
            return {"success": False, "error": "Max copies reached"}
        existing.count += 1
    else:
        db.add(DeckCard(deck_id=deck_id, card_id=card.id, count=1))
    db.commit()
    return {"success": True}


@router.post("/deck/remove-card")
def remove_card_from_deck(
    deck_id: int, card_id: str, db: Session = Depends(get_db),
):
    card = db.query(Card).filter_by(card_id=card_id).first()
    if not card:
        return {"success": False, "error": "Card not found"}

    existing = db.query(DeckCard).filter_by(deck_id=deck_id, card_id=card.id).first()
    if not existing:
        return {"success": False, "error": "Card not in deck"}

    if existing.count > 1:
        existing.count -= 1
    else:
        db.delete(existing)
    db.commit()
    return {"success": True}


@router.post("/deck/import")
def import_deck(
    deckstring: str, name: str = "Imported Deck",
    db: Session = Depends(get_db),
):
    from src.core.deckstring import decode_deckstring
    try:
        decoded = decode_deckstring(deckstring)
    except Exception:
        return {"success": False, "error": "Invalid deckstring"}

    hero_dbf = decoded["hero"]
    # Find hero class from hero card
    hero_card = db.query(Card).filter_by(dbf_id=hero_dbf).first()
    hero_class = hero_card.hero_class if hero_card else "NEUTRAL"

    deck = Deck(name=name, hero_class=hero_class, format="standard",
                deckstring=deckstring, source="manual")
    db.add(deck)
    db.commit()

    for dbf_id, count in decoded["cards"].items():
        card = db.query(Card).filter_by(dbf_id=dbf_id).first()
        if card:
            db.add(DeckCard(deck_id=deck.id, card_id=card.id, count=count))
    db.commit()

    return {"success": True, "deck_id": deck.id}


@router.get("/deck/{deck_id}/export")
def export_deck(deck_id: int, db: Session = Depends(get_db)):
    from src.core.deckstring import encode_deckstring
    deck = db.query(Deck).filter_by(id=deck_id).first()
    if not deck:
        return {"success": False, "error": "Deck not found"}

    deck_cards = (
        db.query(DeckCard, Card)
        .join(Card, DeckCard.card_id == Card.id)
        .filter(DeckCard.deck_id == deck_id)
        .all()
    )

    hero_card = db.query(Card).filter(
        Card.hero_class == deck.hero_class, Card.card_type == "HERO"
    ).first()
    hero_dbf = hero_card.dbf_id if hero_card else 274

    card_dbf_ids = {card.dbf_id: dc.count for dc, card in deck_cards}
    deckstring = encode_deckstring(hero_dbf, card_dbf_ids)

    return {"success": True, "deckstring": deckstring}


@router.post("/deck/ai-recommend")
def ai_recommend(
    hero_class: str, format: str = "standard",
    archetype: str | None = None,
    db: Session = Depends(get_db),
):
    from src.deckbuilder.auto import AutoDeckBuilder
    builder = AutoDeckBuilder(db)
    deck = builder.generate_deck(hero_class=hero_class, format=format, archetype=archetype)
    return deck


@router.post("/simulation/run")
def run_simulation(
    deck_a_id: int, deck_b_id: int, num_matches: int = 10,
    db: Session = Depends(get_db),
):
    # Get deck cards
    results = {"deck_a_wins": 0, "deck_b_wins": 0, "draws": 0, "matches": []}

    deck_a = db.query(Deck).filter_by(id=deck_a_id).first()
    deck_b = db.query(Deck).filter_by(id=deck_b_id).first()
    if not deck_a or not deck_b:
        return {"success": False, "error": "Deck not found"}

    from src.db.tables import DeckCard, Card
    from src.simulator.match import run_match

    def get_deck_data(deck_id):
        rows = (
            db.query(DeckCard, Card)
            .join(Card, DeckCard.card_id == Card.id)
            .filter(DeckCard.deck_id == deck_id).all()
        )
        card_db = {}
        deck_list = []
        for dc, card in rows:
            card_db[card.card_id] = {
                "card_id": card.card_id, "card_type": card.card_type,
                "mana_cost": card.mana_cost, "attack": card.attack or 0,
                "health": card.health or 0, "mechanics": card.mechanics or [],
                "name": card.name,
            }
            for _ in range(dc.count):
                deck_list.append(card.card_id)
        return deck_list, card_db

    deck_a_list, card_db_a = get_deck_data(deck_a_id)
    deck_b_list, card_db_b = get_deck_data(deck_b_id)
    combined_card_db = {**card_db_a, **card_db_b}

    for i in range(min(num_matches, 100)):
        result = run_match(
            deck_a=list(deck_a_list), deck_b=list(deck_b_list),
            hero_a=deck_a.hero_class, hero_b=deck_b.hero_class,
            card_db=combined_card_db, max_turns=45,
        )
        if result.winner == "A":
            results["deck_a_wins"] += 1
        elif result.winner == "B":
            results["deck_b_wins"] += 1
        else:
            results["draws"] += 1

    total = num_matches
    results["deck_a_winrate"] = round(results["deck_a_wins"] / total * 100, 1) if total > 0 else 0
    results["deck_b_winrate"] = round(results["deck_b_wins"] / total * 100, 1) if total > 0 else 0
    results["success"] = True
    return results


@router.get("/tierlist")
def get_tierlist(format: str = "standard", db: Session = Depends(get_db)):
    from src.tierlist.calculator import TierCalculator
    from src.tierlist.ranker import TierRanker

    calc = TierCalculator()
    ranker = TierRanker()
    deck_winrates = calc.get_deck_winrates(db, format_type=format)
    ranked = ranker.rank_decks(deck_winrates)

    tiers = {"S": [], "A": [], "B": [], "C": [], "D": []}
    for deck in ranked:
        tiers[deck["tier"]].append(deck)
    return {"tiers": tiers, "format": format}
