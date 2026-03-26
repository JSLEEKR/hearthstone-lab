from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.tables import Card, Deck, DeckCard
from src.web.i18n import t, get_set_name, get_card_image_url, DEFAULT_LANG

VALID_CLASSES = {"MAGE", "WARRIOR", "HUNTER", "PRIEST", "PALADIN", "ROGUE",
                 "DRUID", "WARLOCK", "SHAMAN", "DEMON_HUNTER", "DEATH_KNIGHT"}

router = APIRouter()


def _get_lang(request: Request) -> str:
    return getattr(request.state, "lang", DEFAULT_LANG)


EXCLUDED_SETS = {"HERO_SKINS"}

RARITY_COLORS = {
    "COMMON": "#888", "RARE": "#0070dd", "EPIC": "#a335ee",
    "LEGENDARY": "#ff8000", "FREE": "#9d9d9d",
}

CARD_TYPE_KO = {
    "MINION": "하수인", "SPELL": "주문", "WEAPON": "무기",
    "HERO": "영웅", "LOCATION": "장소",
}

# Ordered newest to oldest by dbfId range (lower index = newer)
SET_ORDER = [
    # 2025
    "CATACLYSM", "TIME_TRAVEL", "THE_LOST_CITY", "EMERALD_DREAM",
    # 2024
    "SPACE", "ISLAND_VACATION", "WHIZBANGS_WORKSHOP", "WILD_WEST",
    # 2023
    "TITANS", "BATTLE_OF_THE_BANDS", "WONDERS",
    # 2022
    "RETURN_OF_THE_LICH_KING", "PATH_OF_ARTHAS",
    "REVENDRETH", "THE_SUNKEN_CITY", "ALTERAC_VALLEY",
    # 2021
    "STORMWIND", "THE_BARRENS", "DARKMOON_FAIRE",
    # 2020
    "SCHOLOMANCE", "BLACK_TEMPLE", "DRAGONS",
    # 2019
    "ULDUM", "DALARAN", "YEAR_OF_THE_DRAGON",
    # 2018
    "TROLL", "BOOMSDAY", "GILNEAS",
    # 2017
    "LOOTAPALOOZA", "ICECROWN", "UNGORO",
    # 2016
    "GANGS", "KARA", "OG",
    # 2015
    "TGT", "LOE", "BRM",
    # 2014
    "GVG", "NAXX",
    # Evergreen
    "CORE", "PLACEHOLDER_202204", "EXPERT1", "LEGACY", "VANILLA",
    # Other
    "DEMON_HUNTER_INITIATE", "EVENT",
]

SET_NAME_KO = {
    "CORE": "기본", "EXPERT1": "오리지널", "LEGACY": "레거시", "VANILLA": "클래식",
    "NAXX": "낙스라마스", "GVG": "고블린 대 노움", "BRM": "검은바위 산",
    "TGT": "대 마상시합", "LOE": "탐험가 연맹", "OG": "고대 신의 속삭임",
    "KARA": "카라잔", "GANGS": "비열한 거리", "UNGORO": "운고로",
    "ICECROWN": "얼어붙은 왕좌", "LOOTAPALOOZA": "코볼트와 지하 미궁",
    "GILNEAS": "마녀숲", "BOOMSDAY": "박사 붐의 폭심만만 프로젝트",
    "TROLL": "라스타칸의 대난투", "DALARAN": "달라란 대작전",
    "ULDUM": "울둠의 구원자", "DRAGONS": "용의 강림",
    "YEAR_OF_THE_DRAGON": "용의 해", "BLACK_TEMPLE": "황폐한 아웃랜드",
    "SCHOLOMANCE": "스칼로맨스 아카데미", "DARKMOON_FAIRE": "다크문 축제",
    "THE_BARRENS": "불모의 땅", "STORMWIND": "스톰윈드",
    "ALTERAC_VALLEY": "알터랙 계곡", "THE_SUNKEN_CITY": "침몰의 도시",
    "REVENDRETH": "레벤드레스", "RETURN_OF_THE_LICH_KING": "리치왕의 귀환",
    "PATH_OF_ARTHAS": "아서스의 길", "THE_LOST_CITY": "잃어버린 도시",
    "BATTLE_OF_THE_BANDS": "밴드의 전쟁", "TITANS": "타이탄",
    "WILD_WEST": "황야의 땅", "WHIZBANGS_WORKSHOP": "위즈뱅의 작업실",
    "ISLAND_VACATION": "섬 휴가", "EMERALD_DREAM": "에메랄드 꿈",
    "SPACE": "거대한 어둠 너머", "TIME_TRAVEL": "시간 여행", "WONDERS": "경이",
    "GREAT_DARK_BEYOND": "거대한 어둠 너머", "RETURN_TO_UN_GORO": "운고로 귀환",
    "CATACLYSM": "대격변", "DEMON_HUNTER_INITIATE": "악마사냥꾼 입문",
    "EMERALD_DREAM": "에메랄드 꿈속으로",
    "EVENT": "이벤트", "PLACEHOLDER_202204": "과거 코어셋",
}


import re

def _clean_card_text(text: str) -> str:
    """Convert HS markup to readable text."""
    if not text:
        return ""
    # Multiple text variants separated by @ (quest stages etc.) - keep first
    if '@' in text:
        text = text.split('@')[0]
    # $1 -> 1 (damage/heal numbers), #1 -> 1 (buff numbers)
    text = re.sub(r'[\$#](\d+)', r'\1', text)
    # {0}|1(을,를) 예고합니다 -> "카드를 예고합니다" (카드 = no 받침 -> 2nd particle)
    text = re.sub(r'\{0\}\|1\(([^,)]+),([^)]+)\)', r'카드\2', text)
    # {0}, {1} etc. (progress counters, card refs) -> remove
    text = re.sub(r'\{\d+\}', '', text)
    # Empty parentheses left over from placeholder removal
    text = re.sub(r'\(\s*\)', '', text)
    # Strip HTML tags like <b>, </b>, <i>, </i>
    text = re.sub(r'<[^>]+>', '', text)
    # [x] formatting hint
    text = text.replace('[x]', '')
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _query_cards(db: Session, q: str, hero_class: str, cost: int | None,
                 rarity: str, set_name: str, card_type: str,
                 format_filter: str, class_only: str,
                 page: int, per_page: int):
    query = db.query(Card).filter(
        Card.collectible == True,
        Card.set_name.notin_(EXCLUDED_SETS),
    )
    if not card_type:
        # Hide hero skin cards (cost=0 heroes) but keep playable hero cards (cost>0)
        query = query.filter(~((Card.card_type == "HERO") & (Card.mana_cost == 0)))
    if format_filter == "standard":
        query = query.filter(Card.is_standard == True)
    if q:
        query = query.filter(Card.name.ilike(f"%{q}%") | Card.name_ko.ilike(f"%{q}%"))
    if hero_class:
        if class_only == "1":
            query = query.filter(Card.hero_class == hero_class)
        else:
            query = query.filter(Card.hero_class.in_([hero_class, "NEUTRAL"]))
    if cost is not None:
        if cost >= 7:
            query = query.filter(Card.mana_cost >= 7)
        else:
            query = query.filter(Card.mana_cost == cost)
    if rarity:
        query = query.filter(Card.rarity == rarity)
    if set_name:
        query = query.filter(Card.set_name == set_name)
    if card_type:
        query = query.filter(Card.card_type == card_type)

    total = query.count()
    cards = query.order_by(Card.mana_cost, Card.name).offset((page - 1) * per_page).limit(per_page).all()
    return cards, total


def _card_html(c: Card, lang: str = "en") -> str:
    import html as html_mod
    color = RARITY_COLORS.get(c.rarity, "#888")
    type_name = t(f"type.{c.card_type}", lang)
    set_name_display = get_set_name(c.set_name, lang)
    display_name = html_mod.escape((c.name_ko if lang == "ko" else c.name) or c.name)
    name_ko = html_mod.escape(c.name_ko or c.name)
    name_en = html_mod.escape(c.name or "")
    no_effect = t("cards.modal.no_effect", lang)
    image_url = get_card_image_url(c.card_id, lang)
    stats = ""
    if c.card_type == "MINION":
        stats = f'<div class="card-tile-stats"><span>&#9876; {c.attack or 0}</span><span>&#10084; {c.health or 0}</span></div>'
    elif c.card_type == "WEAPON":
        stats = f'<div class="card-tile-stats"><span>&#9876; {c.attack or 0}</span><span>&#128737; {c.durability or 0}</span></div>'
    clean_text = _clean_card_text(c.text or "")
    text_preview = html_mod.escape(clean_text)[:80]
    if len(clean_text) > 80:
        text_preview += "..."
    full_text = html_mod.escape(clean_text or no_effect)
    mechanics_str = html_mod.escape(", ".join(c.mechanics)) if c.mechanics else ""

    return f'''<div class="card-tile" onclick="showCardDetail(this)"
         data-name-ko="{name_ko}" data-name-en="{name_en}"
         data-cost="{c.mana_cost}" data-attack="{c.attack or ''}"
         data-health="{c.health or ''}" data-type="{type_name}"
         data-rarity="{c.rarity}" data-class="{c.hero_class}"
         data-set="{html_mod.escape(set_name_display)}" data-text="{full_text}"
         data-mechanics="{mechanics_str}" data-image="{image_url}"
         data-card-id="{c.card_id}">
        <img src="{image_url}" alt="{display_name}" loading="lazy"
             onerror="this.style.display='none'">
        <div class="card-tile-info">
            <div style="display:flex;align-items:center;gap:0.4rem;">
                <span class="card-cost">{c.mana_cost}</span>
                <span class="card-name">{display_name}</span>
            </div>
            {stats}
            <div class="card-tile-meta" style="color:{color};">
                {type_name} &middot; {set_name_display}
            </div>
            <div class="card-tile-text">{text_preview}</div>
        </div>
    </div>'''


@router.get("/cards")
def search_cards(
    request: Request,
    db: Session = Depends(get_db),
    q: str = "",
    search: str = "",
    hero_class: str = "",
    cost: int | None = None,
    rarity: str = "",
    set_name: str = "",
    card_type: str = "",
    format_filter: str = "",
    class_only: str = "",
    page: int = 1,
    per_page: int = 24,
):
    search_term = q or search  # support both parameter names
    per_page = max(per_page, 1)  # prevent division by zero
    page = max(page, 1)
    cards, total = _query_cards(db, search_term, hero_class, cost, rarity, set_name, card_type, format_filter, class_only, page, per_page)

    lang = _get_lang(request)

    # Return HTML fragment for HTMX requests
    if request.headers.get("HX-Request"):
        html_parts = [_card_html(c, lang) for c in cards]

        total_pages = (total + per_page - 1) // per_page
        prev_label = t("common.previous", lang)
        next_label = t("common.next", lang)
        cards_unit = t("common.cards_unit", lang)
        pagination = ""
        if total_pages > 1:
            pagination = '<div class="card-pagination">'
            if page > 1:
                pagination += f'<button class="btn btn-secondary" hx-get="/api/cards?page={page-1}" hx-target="#card-results" hx-include="[name]">&larr; {prev_label}</button>'
            pagination += f'<span class="pagination-info">{page} / {total_pages} ({total} {cards_unit})</span>'
            if page < total_pages:
                pagination += f'<button class="btn btn-secondary" hx-get="/api/cards?page={page+1}" hx-target="#card-results" hx-include="[name]">{next_label} &rarr;</button>'
            pagination += '</div>'

        return HTMLResponse("".join(html_parts) + pagination)

    # Return JSON for programmatic access
    return {
        "cards": [
            {
                "id": c.id, "card_id": c.card_id, "name": c.name,
                "name_ko": c.name_ko, "mana_cost": c.mana_cost,
                "attack": c.attack, "health": c.health,
                "card_type": c.card_type, "rarity": c.rarity,
                "hero_class": c.hero_class, "set_name": c.set_name,
                "text": c.text,
                "image_url": get_card_image_url(c.card_id, lang),
            }
            for c in cards
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/card/{card_id}")
def get_card_detail(card_id: str, db: Session = Depends(get_db)):
    card = db.query(Card).filter_by(card_id=card_id).first()
    if not card:
        return JSONResponse({"error": "Card not found"}, status_code=404)
    return {
        "card_id": card.card_id, "name": card.name, "name_ko": card.name_ko,
        "mana_cost": card.mana_cost, "attack": card.attack, "health": card.health,
        "durability": card.durability, "card_type": card.card_type,
        "rarity": card.rarity, "hero_class": card.hero_class,
        "set_name": card.set_name, "text": card.text,
        "mechanics": card.mechanics, "image_url": card.image_url,
        "is_standard": card.is_standard,
    }


@router.get("/cards/sets")
def get_card_sets(request: Request, db: Session = Depends(get_db), format_filter: str = ""):
    from sqlalchemy import func
    lang = _get_lang(request)
    query = (
        db.query(Card.set_name, func.count())
        .filter(Card.collectible == True, Card.set_name.notin_(EXCLUDED_SETS),
                ~((Card.card_type == "HERO") & (Card.mana_cost == 0)))
    )
    if format_filter == "standard":
        query = query.filter(Card.is_standard == True)
    sets = query.group_by(Card.set_name).all()
    set_counts = {s: c for s, c in sets}
    result = []
    for s in SET_ORDER:
        if s in set_counts:
            result.append({"set_name": s, "display_name": get_set_name(s, lang), "count": set_counts.pop(s)})
    for s, c in sorted(set_counts.items()):
        result.append({"set_name": s, "display_name": get_set_name(s, lang), "count": c})
    return result


@router.post("/deck/create")
def create_deck(
    name: str, hero_class: str, format: str = "standard",
    db: Session = Depends(get_db),
):
    if hero_class.upper() not in VALID_CLASSES:
        return JSONResponse({"success": False, "error": f"Invalid hero class: {hero_class}"}, status_code=400)
    deck = Deck(name=name, hero_class=hero_class.upper(), format=format, source="manual")
    db.add(deck)
    db.commit()
    return {"deck_id": deck.id, "name": deck.name}


@router.post("/deck/add-card")
def add_card_to_deck(
    deck_id: int, card_id: str, db: Session = Depends(get_db),
):
    card = db.query(Card).filter_by(card_id=card_id).first()
    if not card:
        return JSONResponse({"success": False, "error": "Card not found"}, status_code=404)

    deck = db.query(Deck).filter_by(id=deck_id).first()
    if not deck:
        return JSONResponse({"success": False, "error": "Deck not found"}, status_code=404)

    # Class validation: card must be NEUTRAL or match deck class
    if card.hero_class and card.hero_class not in ("NEUTRAL", deck.hero_class):
        return JSONResponse({"success": False, "error": f"Card class {card.hero_class} doesn't match deck class {deck.hero_class}"}, status_code=400)

    # Enforce 30-card deck limit
    total = sum(dc.count for dc in db.query(DeckCard).filter_by(deck_id=deck_id).all())
    if total >= 30:
        return JSONResponse({"success": False, "error": "Deck is full (30 cards)"}, status_code=400)

    existing = db.query(DeckCard).filter_by(deck_id=deck_id, card_id=card.id).first()
    if existing:
        max_count = 1 if card.rarity == "LEGENDARY" else 2
        if existing.count >= max_count:
            return JSONResponse({"success": False, "error": "Max copies reached"}, status_code=400)
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
        return JSONResponse({"success": False, "error": "Card not found"}, status_code=404)

    existing = db.query(DeckCard).filter_by(deck_id=deck_id, card_id=card.id).first()
    if not existing:
        return JSONResponse({"success": False, "error": "Card not in deck"}, status_code=404)

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

    missing_dbfs = []
    for dbf_id, count in decoded["cards"].items():
        card = db.query(Card).filter_by(dbf_id=dbf_id).first()
        if not card:
            missing_dbfs.append(dbf_id)
            continue
        db.add(DeckCard(deck_id=deck.id, card_id=card.id, count=count))
    db.commit()

    return {"success": True, "deck_id": deck.id,
            "missing_cards": len(missing_dbfs),
            "warning": f"{len(missing_dbfs)} cards not found in database" if missing_dbfs else None}


@router.get("/deck/export")
def export_deck_query(deck_id: int, db: Session = Depends(get_db)):
    return export_deck(deck_id, db)


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
    from src.core.deckstring import encode_deckstring

    builder = AutoDeckBuilder(db)
    result = builder.generate_deck(hero_class=hero_class, format=format, archetype=archetype)

    # Save to DB
    deck = Deck(
        name=f"AI {(archetype or 'midrange').title()} {hero_class}",
        hero_class=hero_class, format=format, source="ai",
    )
    db.add(deck)
    db.commit()

    # Build deckstring and save cards
    card_dbf_map = {}
    for card_info in result["cards"]:
        card = db.query(Card).filter_by(card_id=card_info["card_id"]).first()
        if card:
            count = card_info.get("count", 1)
            db.add(DeckCard(deck_id=deck.id, card_id=card.id, count=count))
            card_dbf_map[card.dbf_id] = card_dbf_map.get(card.dbf_id, 0) + count
    db.commit()

    # Generate deckstring
    hero_card = db.query(Card).filter(
        Card.hero_class == hero_class, Card.card_type == "HERO"
    ).first()
    hero_dbf = hero_card.dbf_id if hero_card else 274
    deckstring = encode_deckstring(hero_dbf, card_dbf_map)

    result["success"] = True
    result["deck_id"] = deck.id
    result["deckstring"] = deckstring
    return result


@router.post("/simulation/run")
def run_simulation(
    deck_a_id: int, deck_b_id: int, num_matches: int = 10,
    include_logs: bool = True,
    db: Session = Depends(get_db),
):
    if num_matches < 1:
        return JSONResponse({"success": False, "error": "num_matches must be at least 1"}, status_code=400)

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
                "health": card.health or 0, "durability": card.durability or 1,
                "mechanics": card.mechanics or [],
                "name": card.name, "text": card.text or "",
                "rarity": card.rarity or "",
            }
            for _ in range(dc.count):
                deck_list.append(card.card_id)
        return deck_list, card_db

    deck_a_list, card_db_a = get_deck_data(deck_a_id)
    deck_b_list, card_db_b = get_deck_data(deck_b_id)
    combined_card_db = {**card_db_a, **card_db_b}

    actual_matches = min(num_matches, 100)
    match_logs = []
    for i in range(actual_matches):
        result = run_match(
            deck_a=list(deck_a_list), deck_b=list(deck_b_list),
            hero_a=deck_a.hero_class, hero_b=deck_b.hero_class,
            card_db=combined_card_db, max_turns=60,
        )
        if result.winner == "A":
            results["deck_a_wins"] += 1
        elif result.winner == "B":
            results["deck_b_wins"] += 1
        else:
            results["draws"] += 1

        match_logs.append({
            "game_num": i + 1,
            "winner": result.winner,
            "turns": result.turns,
            "p1_hero": result.p1_hero,
            "p2_hero": result.p2_hero,
            "log": result.log if include_logs else [],
        })

    results["deck_a_winrate"] = round(results["deck_a_wins"] / actual_matches * 100, 1) if actual_matches > 0 else 0
    results["deck_b_winrate"] = round(results["deck_b_wins"] / actual_matches * 100, 1) if actual_matches > 0 else 0
    results["match_logs"] = match_logs
    results["success"] = True
    return results


@router.post("/simulation/run-single")
def run_single_match(
    deck_a_id: int, deck_b_id: int,
    db: Session = Depends(get_db),
):
    """Run exactly 1 match and return full event log."""
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
                "health": card.health or 0, "durability": card.durability or 1,
                "mechanics": card.mechanics or [],
                "name": card.name, "text": card.text or "",
                "rarity": card.rarity or "",
            }
            for _ in range(dc.count):
                deck_list.append(card.card_id)
        return deck_list, card_db

    deck_a_list, card_db_a = get_deck_data(deck_a_id)
    deck_b_list, card_db_b = get_deck_data(deck_b_id)
    combined_card_db = {**card_db_a, **card_db_b}

    result = run_match(
        deck_a=list(deck_a_list), deck_b=list(deck_b_list),
        hero_a=deck_a.hero_class, hero_b=deck_b.hero_class,
        card_db=combined_card_db, max_turns=60,
    )
    return {
        "success": True,
        "winner": result.winner,
        "turns": result.turns,
        "p1_hero": result.p1_hero,
        "p2_hero": result.p2_hero,
        "log": result.log,
    }


@router.post("/tournament/run")
def run_tournament(
    request: Request,
    deck_ids: str,
    matches_per_pair: int = 20,
    ai_level: str = "rule",
    db: Session = Depends(get_db),
):
    from src.simulator.tournament import Tournament
    from src.simulator.ai import RuleBasedAI, ScoreBasedAI, MCTSAI

    if ai_level == "mcts":
        ai_class = MCTSAI(iterations=50)
    elif ai_level == "score":
        ai_class = ScoreBasedAI
    else:
        ai_class = RuleBasedAI

    try:
        ids = [int(x.strip()) for x in deck_ids.split(",") if x.strip()]
    except ValueError:
        return JSONResponse({"success": False, "error": "Invalid deck_ids: must be comma-separated integers"}, status_code=400)
    if len(ids) < 2:
        return JSONResponse({"success": False, "error": "Need at least 2 decks"}, status_code=400)

    from src.db.tables import DeckCard, Card
    decks_data = {}
    combined_card_db = {}

    for deck_id in ids:
        deck = db.query(Deck).filter_by(id=deck_id).first()
        if not deck:
            return {"success": False, "error": f"Deck {deck_id} not found"}

        rows = (
            db.query(DeckCard, Card)
            .join(Card, DeckCard.card_id == Card.id)
            .filter(DeckCard.deck_id == deck_id).all()
        )
        deck_list = []
        for dc, card in rows:
            combined_card_db[card.card_id] = {
                "card_id": card.card_id, "card_type": card.card_type,
                "mana_cost": card.mana_cost, "attack": card.attack or 0,
                "health": card.health or 0, "durability": card.durability or 1,
                "mechanics": card.mechanics or [],
                "name": card.name, "text": card.text or "",
                "rarity": card.rarity or "",
            }
            for _ in range(dc.count):
                deck_list.append(card.card_id)
        decks_data[deck.name] = {"hero": deck.hero_class, "cards": deck_list}

    t = Tournament(decks_data, combined_card_db,
                   matches_per_pair=min(matches_per_pair, 100),
                   ai_class=ai_class)
    result = t.run()
    return {
        "success": True,
        "rankings": result.rankings,
        "matchups": result.matchups,
        "matrix": result.matrix,
        "summary": result.summary(),
    }


@router.get("/decks")
def list_decks(db: Session = Depends(get_db)):
    decks = db.query(Deck).all()
    return {"decks": [
        {"id": d.id, "name": d.name, "hero_class": d.hero_class,
         "format": d.format, "source": d.source,
         "card_count": db.query(func.sum(DeckCard.count)).filter_by(deck_id=d.id).scalar() or 0}
        for d in decks
    ]}


@router.get("/deck/{deck_id}/cards")
def get_deck_cards(deck_id: int, request: Request, db: Session = Depends(get_db)):
    """Return deck card list for preview panels."""
    deck = db.query(Deck).filter_by(id=deck_id).first()
    if not deck:
        return JSONResponse({"error": "Deck not found"}, status_code=404)

    lang = _get_lang(request)
    rows = (
        db.query(DeckCard, Card)
        .join(Card, DeckCard.card_id == Card.id)
        .filter(DeckCard.deck_id == deck_id)
        .order_by(Card.mana_cost, Card.name)
        .all()
    )
    name_field = "name_ko" if lang == "ko" else "name"
    cards = [
        {
            "card_id": card.card_id,
            "name": getattr(card, name_field) or card.name,
            "mana_cost": card.mana_cost,
            "count": dc.count,
            "rarity": card.rarity,
            "card_type": card.card_type,
        }
        for dc, card in rows
    ]
    return {"deck_name": deck.name, "hero_class": deck.hero_class, "cards": cards}


@router.post("/simulation/import-deck")
def import_deck_for_sim(
    deckstring: str, name: str = "Imported",
    db: Session = Depends(get_db),
):
    """Import a deckstring and save to DB for simulation use."""
    from src.core.deckstring import decode_deckstring
    try:
        decoded = decode_deckstring(deckstring)
    except Exception:
        return {"success": False, "error": "Invalid deckstring"}

    hero_dbf = decoded["hero"]
    hero_card = db.query(Card).filter_by(dbf_id=hero_dbf).first()
    hero_class = hero_card.hero_class if hero_card else "NEUTRAL"

    deck = Deck(name=name, hero_class=hero_class, format="standard",
                deckstring=deckstring, source="manual")
    db.add(deck)
    db.commit()

    missing_dbfs = []
    for dbf_id, count in decoded["cards"].items():
        card = db.query(Card).filter_by(dbf_id=dbf_id).first()
        if not card:
            missing_dbfs.append(dbf_id)
            continue
        db.add(DeckCard(deck_id=deck.id, card_id=card.id, count=count))
    db.commit()

    return {"success": True, "deck_id": deck.id,
            "missing_cards": len(missing_dbfs),
            "warning": f"{len(missing_dbfs)} cards not found in database" if missing_dbfs else None}


@router.post("/meta/run")
def run_meta_builder(
    classes: str = "",
    archetypes: str = "",
    matches_per_pair: int = 10,
    optimization_generations: int = 2,
    max_decks_per_class: int = 2,
    db: Session = Depends(get_db),
):
    """Run the full meta deck building pipeline."""
    from src.deckbuilder.meta import MetaDeckBuilder
    try:
        builder = MetaDeckBuilder(
            db,
            classes=[c.strip() for c in classes.split(",") if c.strip()] or None,
            archetypes=[a.strip() for a in archetypes.split(",") if a.strip()] or None,
            matches_per_pair=min(matches_per_pair, 50),
            optimization_generations=min(optimization_generations, 5),
            max_decks_per_class=min(max_decks_per_class, 5),
        )
        report = builder.run()
        return {
            "success": True,
            "tier_list": [
                {"name": e.deck_name, "hero_class": e.hero_class,
                 "archetype": e.archetype, "tier": e.tier, "winrate": e.winrate}
                for e in report.tier_list
            ],
            "total_decks": report.total_decks,
            "total_matches": report.total_matches,
        }
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/optimize/analyze")
def analyze_deck(deck_id: int, db: Session = Depends(get_db)):
    """Run baseline analysis on a deck to identify underperformers."""
    deck = db.query(Deck).filter_by(id=deck_id).first()
    if not deck:
        return JSONResponse({"success": False, "error": "Deck not found"}, status_code=404)

    # Build card_db and deck data
    from src.deckbuilder.card_optimizer import CardDeckOptimizer
    deck_data, card_db, opponents = _build_optimizer_data(deck_id, db)
    if not deck_data:
        return {"success": False, "error": "Deck has no cards"}

    try:
        optimizer = CardDeckOptimizer(
            card_db=card_db,
            opponent_decks=opponents,
            games_per_eval=30,
            max_replacements=0,  # analyze only, no replacements
        )
        report = optimizer.optimize_deck(deck_data)
        return {
            "success": True,
            "original_winrate": report.original_winrate,
            "optimized_winrate": report.original_winrate,
            "underperformers": report.underperformers[:10],
            "card_changes": [],
        }
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/optimize/run")
def run_optimizer(deck_id: int, db: Session = Depends(get_db)):
    """Run full optimization on a deck."""
    deck = db.query(Deck).filter_by(id=deck_id).first()
    if not deck:
        return JSONResponse({"success": False, "error": "Deck not found"}, status_code=404)

    from src.deckbuilder.card_optimizer import CardDeckOptimizer
    deck_data, card_db, opponents = _build_optimizer_data(deck_id, db)
    if not deck_data:
        return {"success": False, "error": "Deck has no cards"}

    try:
        optimizer = CardDeckOptimizer(
            card_db=card_db,
            opponent_decks=opponents,
            games_per_eval=30,
            max_replacements=5,
        )
        report = optimizer.optimize_deck(deck_data)
        return {
            "success": True,
            "original_winrate": report.original_winrate,
            "optimized_winrate": report.optimized_winrate,
            "underperformers": report.underperformers[:10],
            "card_changes": [
                {
                    "card_removed": ch.card_removed,
                    "card_removed_name": ch.card_removed_name,
                    "card_added": ch.card_added,
                    "card_added_name": ch.card_added_name,
                    "original_winrate": ch.original_winrate,
                    "new_winrate": ch.new_winrate,
                    "delta": ch.delta,
                    "z_score": ch.z_score,
                    "significant": ch.significant,
                    "games_played": ch.games_played,
                }
                for ch in report.card_changes
            ],
        }
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


def _build_optimizer_data(deck_id: int, db: Session):
    """Helper to build deck data, card_db, and opponent list for optimizer."""
    deck = db.query(Deck).filter_by(id=deck_id).first()
    if not deck:
        return None, {}, []

    rows = (
        db.query(DeckCard, Card)
        .join(Card, DeckCard.card_id == Card.id)
        .filter(DeckCard.deck_id == deck_id).all()
    )
    if not rows:
        return None, {}, []

    card_db = {}
    deck_list = []
    for dc, card in rows:
        card_db[card.card_id] = {
            "card_id": card.card_id, "card_type": card.card_type,
            "mana_cost": card.mana_cost, "attack": card.attack or 0,
            "health": card.health or 0, "durability": card.durability or 1,
            "mechanics": card.mechanics or [],
            "name": card.name, "text": card.text or "",
            "rarity": card.rarity or "",
            "hero_class": card.hero_class or "NEUTRAL",
        }
        for _ in range(dc.count):
            deck_list.append(card.card_id)

    deck_data = {
        "name": deck.name,
        "hero": deck.hero_class,
        "cards": deck_list,
    }

    # Build opponent decks from other decks in DB (up to 5)
    opponents = []
    other_decks = db.query(Deck).filter(Deck.id != deck_id).order_by(Deck.created_at.desc()).limit(5).all()
    for od in other_decks:
        orows = (
            db.query(DeckCard, Card)
            .join(Card, DeckCard.card_id == Card.id)
            .filter(DeckCard.deck_id == od.id).all()
        )
        if not orows:
            continue
        opp_cards = []
        for odc, ocard in orows:
            if ocard.card_id not in card_db:
                card_db[ocard.card_id] = {
                    "card_id": ocard.card_id, "card_type": ocard.card_type,
                    "mana_cost": ocard.mana_cost, "attack": ocard.attack or 0,
                    "health": ocard.health or 0, "durability": ocard.durability or 1,
                    "mechanics": ocard.mechanics or [],
                    "name": ocard.name, "text": ocard.text or "",
                    "rarity": ocard.rarity or "",
                    "hero_class": ocard.hero_class or "NEUTRAL",
                }
            for _ in range(odc.count):
                opp_cards.append(ocard.card_id)
        opponents.append({
            "name": od.name,
            "hero": od.hero_class,
            "cards": opp_cards,
        })

    # Also add all standard collectible cards to card_db for replacement candidates
    all_cards = db.query(Card).filter(
        Card.is_standard == True,
        Card.collectible == True,
    ).all()
    for c in all_cards:
        if c.card_id not in card_db:
            card_db[c.card_id] = {
                "card_id": c.card_id, "card_type": c.card_type,
                "mana_cost": c.mana_cost, "attack": c.attack or 0,
                "health": c.health or 0, "durability": c.durability or 1,
                "mechanics": c.mechanics or [],
                "name": c.name, "text": c.text or "",
                "rarity": c.rarity or "",
                "hero_class": c.hero_class or "NEUTRAL",
            }

    return deck_data, card_db, opponents


@router.delete("/deck/{deck_id}")
def delete_deck(deck_id: int, db: Session = Depends(get_db)):
    deck = db.query(Deck).filter_by(id=deck_id).first()
    if not deck:
        return JSONResponse({"success": False, "error": "Deck not found"}, status_code=404)
    db.query(DeckCard).filter_by(deck_id=deck_id).delete()
    db.delete(deck)
    db.commit()
    return {"success": True}


