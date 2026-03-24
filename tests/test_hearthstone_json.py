import pytest
from unittest.mock import AsyncMock, patch
from src.collector.hearthstone_json import HearthstoneJsonClient


SAMPLE_CARDS_KO = [
    {
        "id": "CS2_182", "dbfId": 1369, "name": "칠풍의 예티",
        "type": "MINION", "cardClass": "NEUTRAL", "cost": 4,
        "attack": 4, "health": 5, "rarity": "FREE", "set": "CORE",
        "collectible": True, "text": "", "mechanics": [],
    },
    {
        "id": "CS2_029", "dbfId": 522, "name": "화염구",
        "type": "SPELL", "cardClass": "MAGE", "cost": 4,
        "rarity": "FREE", "set": "CORE", "collectible": True,
        "text": "피해를 <b>6</b>만큼 줍니다.", "mechanics": [],
    },
    {
        "id": "HIDDEN_001", "dbfId": 9999, "name": "숨겨진카드",
        "type": "ENCHANTMENT", "cardClass": "NEUTRAL", "cost": 0, "set": "CORE",
    },
]

SAMPLE_CARDS_EN = [
    {
        "id": "CS2_182", "dbfId": 1369, "name": "Chillwind Yeti",
        "type": "MINION", "cardClass": "NEUTRAL", "cost": 4,
        "attack": 4, "health": 5, "rarity": "FREE", "set": "CORE",
        "collectible": True, "text": "", "mechanics": [],
    },
    {
        "id": "CS2_029", "dbfId": 522, "name": "Fireball",
        "type": "SPELL", "cardClass": "MAGE", "cost": 4,
        "rarity": "FREE", "set": "CORE", "collectible": True,
        "text": "Deal <b>6</b> damage.", "mechanics": [],
    },
]


@pytest.mark.asyncio
async def test_fetch_cards_filters_collectible():
    client = HearthstoneJsonClient(base_url="https://fake.api")
    mock_response_ko = AsyncMock()
    mock_response_ko.json.return_value = SAMPLE_CARDS_KO
    mock_response_ko.raise_for_status = lambda: None
    mock_response_en = AsyncMock()
    mock_response_en.json.return_value = SAMPLE_CARDS_EN
    mock_response_en.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.get", side_effect=[mock_response_ko, mock_response_en]):
        cards = await client.fetch_cards()

    assert len(cards) == 2
    assert cards[0]["card_id"] == "CS2_182"
    assert cards[0]["name"] == "Chillwind Yeti"
    assert cards[0]["name_ko"] == "칠풍의 예티"


@pytest.mark.asyncio
async def test_fetch_cards_maps_fields_correctly():
    client = HearthstoneJsonClient(base_url="https://fake.api")
    mock_response_ko = AsyncMock()
    mock_response_ko.json.return_value = [SAMPLE_CARDS_KO[1]]
    mock_response_ko.raise_for_status = lambda: None
    mock_response_en = AsyncMock()
    mock_response_en.json.return_value = [SAMPLE_CARDS_EN[1]]
    mock_response_en.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.get", side_effect=[mock_response_ko, mock_response_en]):
        cards = await client.fetch_cards()

    card = cards[0]
    assert card["card_id"] == "CS2_029"
    assert card["dbf_id"] == 522
    assert card["name"] == "Fireball"
    assert card["name_ko"] == "화염구"
    assert card["card_type"] == "SPELL"
    assert card["hero_class"] == "MAGE"
    assert card["mana_cost"] == 4
