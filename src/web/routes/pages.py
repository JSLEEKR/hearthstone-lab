from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.web.templates_config import templates
from src.web.i18n import get_all_translations, t, get_card_image_url

router = APIRouter()


def _ctx(request: Request, **kwargs) -> dict:
    """Build template context with i18n translations."""
    lang = getattr(request.state, "lang", "en")
    return {"request": request, "lang": lang, "t": get_all_translations(lang), **kwargs}


@router.get("/")
def home_page(request: Request):
    return templates.TemplateResponse(request, "builder.html", _ctx(request))


@router.get("/cards")
def cards_page(request: Request):
    return templates.TemplateResponse(request, "cards.html", _ctx(request))


@router.get("/builder")
def builder_page(request: Request):
    return templates.TemplateResponse(request, "builder.html", _ctx(request))


@router.get("/deck/{deck_id}")
def deck_detail_page(request: Request, deck_id: int, db: Session = Depends(get_db)):
    from src.db.tables import Deck, DeckCard, Card
    deck = db.query(Deck).filter_by(id=deck_id).first()
    if not deck:
        from fastapi.responses import HTMLResponse
        return HTMLResponse("<h1>Deck not found</h1>", status_code=404)

    lang = getattr(request.state, "lang", "en")
    cards = (
        db.query(DeckCard, Card)
        .join(Card, DeckCard.card_id == Card.id)
        .filter(DeckCard.deck_id == deck_id)
        .order_by(Card.mana_cost, Card.name)
        .all()
    )
    name_field = "name_ko" if lang == "ko" else "name"
    deck_cards = [
        {"name": getattr(c, name_field) or c.name, "mana_cost": c.mana_cost,
         "count": dc.count, "rarity": c.rarity, "card_id": c.card_id,
         "card_type": c.card_type}
        for dc, c in cards
    ]

    curve = {}
    for card in deck_cards:
        cost = min(card["mana_cost"], 7)
        curve[cost] = curve.get(cost, 0) + card["count"]
    mana_curve = [curve.get(i, 0) for i in range(8)]

    return templates.TemplateResponse(request, "deck.html", _ctx(
        request, deck=deck, cards=deck_cards, mana_curve=mana_curve,
    ))


@router.get("/simulation")
def simulation_page(request: Request, db: Session = Depends(get_db)):
    from src.db.tables import Deck
    decks = db.query(Deck).order_by(Deck.created_at.desc()).limit(50).all()
    return templates.TemplateResponse(request, "simulation.html", _ctx(
        request, decks=decks,
    ))


@router.get("/tournament")
def tournament_page(request: Request, db: Session = Depends(get_db)):
    from src.db.tables import Deck, DeckCard
    decks = db.query(Deck).order_by(Deck.created_at.desc()).limit(50).all()
    decks_with_counts = []
    for d in decks:
        count = db.query(func.sum(DeckCard.count)).filter_by(deck_id=d.id).scalar() or 0
        decks_with_counts.append(type('Deck', (), {
            'id': d.id, 'name': d.name, 'hero_class': d.hero_class,
            'card_count': int(count),
        })())
    return templates.TemplateResponse(request, "tournament.html", _ctx(
        request, decks=decks_with_counts,
    ))


@router.get("/meta")
def meta_page(request: Request):
    return templates.TemplateResponse(request, "meta.html", _ctx(request))


@router.get("/optimize")
def optimize_page(request: Request, db: Session = Depends(get_db)):
    from src.db.tables import Deck
    decks = db.query(Deck).order_by(Deck.created_at.desc()).limit(50).all()
    return templates.TemplateResponse(request, "optimize.html", _ctx(
        request, decks=decks,
    ))


@router.get("/harness")
def harness_page(request: Request):
    return templates.TemplateResponse(request, "harness.html", _ctx(request))
