from __future__ import annotations

AGGRO_MAX_AVG_COST = 3.0
MIDRANGE_MAX_AVG_COST = 4.5
COMBO_SPELL_RATIO = 0.45


def classify_archetype(deck_stats: dict) -> str:
    avg_cost = deck_stats.get("avg_mana_cost", 0)
    spell_ratio = deck_stats.get("spell_ratio", 0)
    has_combo = deck_stats.get("has_combo_pieces", False)

    if has_combo and spell_ratio >= COMBO_SPELL_RATIO:
        return "combo"
    if avg_cost <= AGGRO_MAX_AVG_COST:
        return "aggro"
    if avg_cost <= MIDRANGE_MAX_AVG_COST:
        return "midrange"
    return "control"


def classify_from_cards(cards: list[dict]) -> str:
    if not cards:
        return "midrange"

    total_cost = 0
    total_cards = 0
    spell_count = 0

    for c in cards:
        count = c.get("count", 1)
        total_cost += c.get("mana_cost", 0) * count
        total_cards += count
        if c.get("card_type") == "SPELL":
            spell_count += count

    avg_cost = total_cost / total_cards if total_cards > 0 else 0
    spell_ratio = spell_count / total_cards if total_cards > 0 else 0

    return classify_archetype({
        "avg_mana_cost": avg_cost,
        "spell_ratio": spell_ratio,
        "has_combo_pieces": False,
    })
