"""Deckstring encode/decode compatible with Hearthstone deck codes.

Format: base64 encoded varint stream.
Structure: [reserved=0] [version=1] [format] [1 hero] [single-copy cards] [double-copy cards]
"""
from __future__ import annotations

import base64
from io import BytesIO


def _write_varint(stream: BytesIO, value: int):
    while value > 0x7F:
        stream.write(bytes([0x80 | (value & 0x7F)]))
        value >>= 7
    stream.write(bytes([value & 0x7F]))


def _read_varint(stream: BytesIO) -> int:
    result = 0
    shift = 0
    while True:
        byte = stream.read(1)
        if not byte:
            raise ValueError("Unexpected end of stream")
        b = byte[0]
        result |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            break
        shift += 7
    return result


def encode_deckstring(hero_dbf_id: int, card_dbf_ids: dict[int, int], format_type: int = 2) -> str:
    singles = sorted([dbf for dbf, count in card_dbf_ids.items() if count == 1])
    doubles = sorted([dbf for dbf, count in card_dbf_ids.items() if count == 2])

    stream = BytesIO()
    _write_varint(stream, 0)  # reserved
    _write_varint(stream, 1)  # version
    _write_varint(stream, format_type)

    _write_varint(stream, 1)  # hero count
    _write_varint(stream, hero_dbf_id)

    _write_varint(stream, len(singles))
    for dbf in singles:
        _write_varint(stream, dbf)

    _write_varint(stream, len(doubles))
    for dbf in doubles:
        _write_varint(stream, dbf)

    n_copies = [(dbf, count) for dbf, count in card_dbf_ids.items() if count > 2]
    _write_varint(stream, len(n_copies))
    for dbf, count in sorted(n_copies):
        _write_varint(stream, dbf)
        _write_varint(stream, count)

    return base64.b64encode(stream.getvalue()).decode("ascii")


def decode_deckstring(deckstring: str) -> dict:
    data = base64.b64decode(deckstring)
    stream = BytesIO(data)

    _read_varint(stream)  # reserved
    _read_varint(stream)  # version
    format_type = _read_varint(stream)

    hero_count = _read_varint(stream)
    heroes = [_read_varint(stream) for _ in range(hero_count)]

    cards: dict[int, int] = {}

    single_count = _read_varint(stream)
    for _ in range(single_count):
        dbf = _read_varint(stream)
        cards[dbf] = 1

    double_count = _read_varint(stream)
    for _ in range(double_count):
        dbf = _read_varint(stream)
        cards[dbf] = 2

    n_count = _read_varint(stream)
    for _ in range(n_count):
        dbf = _read_varint(stream)
        count = _read_varint(stream)
        cards[dbf] = count

    return {
        "hero": heroes[0] if heroes else 0,
        "format": format_type,
        "cards": cards,
    }
