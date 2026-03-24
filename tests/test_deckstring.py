import pytest
from src.core.deckstring import encode_deckstring, decode_deckstring


class TestDeckstring:
    def test_encode_and_decode_roundtrip(self):
        hero_id = 274  # Jaina (Mage)
        card_dbf_ids = {
            522: 2,    # Fireball x2
            1369: 2,   # Chillwind Yeti x2
            179: 1,    # Archmage Antonidas x1 (legendary)
        }
        format_type = 2  # standard

        encoded = encode_deckstring(hero_id, card_dbf_ids, format_type)
        assert isinstance(encoded, str)

        result = decode_deckstring(encoded)
        assert result["hero"] == hero_id
        assert result["format"] == format_type
        assert result["cards"] == card_dbf_ids

    def test_decode_known_deckstring(self):
        hero_id = 274
        cards = {522: 2, 1369: 2}
        encoded = encode_deckstring(hero_id, cards, 2)
        decoded = decode_deckstring(encoded)
        assert decoded["hero"] == 274
        assert decoded["cards"][522] == 2
        assert decoded["cards"][1369] == 2

    def test_encode_empty_deck(self):
        encoded = encode_deckstring(274, {}, 2)
        decoded = decode_deckstring(encoded)
        assert decoded["hero"] == 274
        assert decoded["cards"] == {}

    def test_encode_separates_single_and_double(self):
        cards = {100: 1, 200: 2, 300: 1}
        encoded = encode_deckstring(274, cards, 2)
        decoded = decode_deckstring(encoded)
        assert decoded["cards"][100] == 1
        assert decoded["cards"][200] == 2
        assert decoded["cards"][300] == 1
