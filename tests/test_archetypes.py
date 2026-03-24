from src.deckbuilder.archetypes import classify_archetype


def _make_deck_stats(avg_cost: float, spell_ratio: float, has_combo_pieces: bool = False):
    return {"avg_mana_cost": avg_cost, "spell_ratio": spell_ratio,
            "has_combo_pieces": has_combo_pieces}


class TestArchetypeClassification:
    def test_aggro_low_curve(self):
        result = classify_archetype(_make_deck_stats(avg_cost=2.0, spell_ratio=0.2))
        assert result == "aggro"

    def test_control_high_curve(self):
        result = classify_archetype(_make_deck_stats(avg_cost=5.5, spell_ratio=0.4))
        assert result == "control"

    def test_midrange_medium_curve(self):
        result = classify_archetype(_make_deck_stats(avg_cost=3.5, spell_ratio=0.3))
        assert result == "midrange"

    def test_combo_with_combo_pieces(self):
        result = classify_archetype(_make_deck_stats(avg_cost=4.0, spell_ratio=0.5,
                                                      has_combo_pieces=True))
        assert result == "combo"

    def test_classify_from_card_list(self):
        from src.deckbuilder.archetypes import classify_from_cards
        cards = [
            {"mana_cost": 1, "card_type": "MINION", "count": 2},
            {"mana_cost": 2, "card_type": "MINION", "count": 2},
            {"mana_cost": 1, "card_type": "SPELL", "count": 2},
            {"mana_cost": 3, "card_type": "MINION", "count": 2},
        ]
        result = classify_from_cards(cards)
        assert result in ("aggro", "midrange", "control", "combo")
