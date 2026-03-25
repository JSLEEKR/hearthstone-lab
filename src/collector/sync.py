from __future__ import annotations
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.db.tables import Card

logger = logging.getLogger(__name__)

# Sets that are currently in Standard rotation (updated yearly around April)
STANDARD_SETS = {
    "CORE", "PATH_OF_ARTHAS", "BATTLE_OF_THE_BANDS", "TITANS",
    "WILD_WEST", "WHIZBANGS_WORKSHOP", "ISLAND_VACATION",
    "GREAT_DARK_BEYOND", "RETURN_TO_UN_GORO",
}


def _is_standard_set(set_name: str) -> bool:
    return set_name.upper().replace("'", "").replace(" ", "_") in STANDARD_SETS


def sync_cards_to_db(db: Session, hs_json_cards: list[dict], blizzard_cards: list[dict]) -> dict[str, int]:
    blizzard_by_dbf: dict[int, dict] = {}
    for bc in blizzard_cards:
        blizzard_by_dbf[bc["dbf_id"]] = bc

    existing: dict[str, Card] = {}
    for card in db.query(Card).all():
        existing[card.card_id] = card

    inserted = 0
    updated = 0

    for hc in hs_json_cards:
        card_id = hc["card_id"]
        dbf_id = hc["dbf_id"]

        json_data = dict(hc.get("json_data") or {})
        blizzard = blizzard_by_dbf.get(dbf_id, {})
        if blizzard.get("flavor_text"):
            json_data["flavor_text"] = blizzard["flavor_text"]

        is_standard = _is_standard_set(hc.get("set_name", ""))

        if card_id in existing:
            card = existing[card_id]
            changed = False
            for field in ("name", "name_ko", "card_type", "hero_class", "mana_cost",
                          "attack", "health", "durability", "text", "rarity",
                          "set_name", "mechanics", "collectible"):
                new_val = hc.get(field)
                if getattr(card, field) != new_val:
                    setattr(card, field, new_val)
                    changed = True
            if card.is_standard != is_standard:
                card.is_standard = is_standard
                changed = True
            if card.json_data != json_data:
                card.json_data = json_data
                changed = True
            if changed:
                card.updated_at = datetime.now(timezone.utc)
                updated += 1
        else:
            card = Card(
                card_id=card_id, dbf_id=dbf_id, name=hc["name"], name_ko=hc["name_ko"],
                card_type=hc["card_type"], hero_class=hc["hero_class"],
                mana_cost=hc["mana_cost"], attack=hc.get("attack"),
                health=hc.get("health"), durability=hc.get("durability"),
                text=hc.get("text", ""), rarity=hc["rarity"], set_name=hc["set_name"],
                mechanics=hc.get("mechanics", []), collectible=hc.get("collectible", True),
                is_standard=is_standard,
                json_data=json_data,
                image_url=f"https://art.hearthstonejson.com/v1/render/latest/koKR/512x/{card_id}.png",
            )
            db.add(card)
            inserted += 1

    db.commit()
    logger.info("Card sync complete: %d inserted, %d updated", inserted, updated)
    return {"inserted": inserted, "updated": updated}
