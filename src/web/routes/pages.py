from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.web.templates_config import templates

router = APIRouter()


@router.get("/")
def tierlist_page(request: Request, format: str = "standard", db: Session = Depends(get_db)):
    from src.tierlist.calculator import TierCalculator
    from src.tierlist.ranker import TierRanker

    calc = TierCalculator()
    ranker = TierRanker()
    deck_winrates = calc.get_deck_winrates(db, format_type=format)
    ranked = ranker.rank_decks(deck_winrates)

    tiers = {"S": [], "A": [], "B": [], "C": [], "D": []}
    for deck in ranked:
        tiers[deck["tier"]].append(deck)

    return templates.TemplateResponse(request, "tierlist.html", {
        "tiers": tiers, "format": format,
    })


@router.get("/cards")
def cards_page(request: Request):
    return templates.TemplateResponse(request, "cards.html")


@router.get("/builder")
def builder_page(request: Request):
    return templates.TemplateResponse(request, "builder.html")


@router.get("/deck/{deck_id}")
def deck_detail_page(request: Request, deck_id: int, db: Session = Depends(get_db)):
    from src.db.tables import Deck, DeckCard, Card
    deck = db.query(Deck).filter_by(id=deck_id).first()
    if not deck:
        from fastapi.responses import HTMLResponse
        return HTMLResponse("<h1>Deck not found</h1>", status_code=404)

    cards = (
        db.query(DeckCard, Card)
        .join(Card, DeckCard.card_id == Card.id)
        .filter(DeckCard.deck_id == deck_id)
        .order_by(Card.mana_cost, Card.name)
        .all()
    )
    deck_cards = [
        {"name": c.name, "name_ko": c.name_ko, "mana_cost": c.mana_cost,
         "count": dc.count, "rarity": c.rarity, "card_id": c.card_id,
         "card_type": c.card_type}
        for dc, c in cards
    ]

    # Mana curve data
    curve = {}
    for card in deck_cards:
        cost = min(card["mana_cost"], 7)
        curve[cost] = curve.get(cost, 0) + card["count"]
    mana_curve = [curve.get(i, 0) for i in range(8)]

    return templates.TemplateResponse(request, "deck.html", {
        "deck": deck, "cards": deck_cards,
        "mana_curve": mana_curve,
    })


@router.get("/simulation")
def simulation_page(request: Request, db: Session = Depends(get_db)):
    from src.db.tables import Deck
    decks = db.query(Deck).order_by(Deck.created_at.desc()).limit(50).all()
    return templates.TemplateResponse(request, "simulation.html", {
        "decks": decks,
    })
