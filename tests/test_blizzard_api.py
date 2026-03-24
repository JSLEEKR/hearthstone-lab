import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from src.collector.blizzard_api import BlizzardApiClient


@pytest.mark.asyncio
async def test_get_access_token():
    client = BlizzardApiClient(client_id="test_id", client_secret="test_secret")
    mock_response = AsyncMock()
    mock_response.json.return_value = {"access_token": "test_token", "expires_in": 86399}
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        token = await client._get_access_token()
    assert token == "test_token"


@pytest.mark.asyncio
async def test_fetch_cards_single_page():
    client = BlizzardApiClient(client_id="test_id", client_secret="test_secret")
    client._access_token = "cached_token"

    page1_response = AsyncMock()
    page1_response.json.return_value = {
        "cards": [{
            "id": 1369, "slug": "1369-chillwind-yeti", "name": "Chillwind Yeti",
            "cardTypeId": 4, "classId": 12, "manaCost": 4, "attack": 4, "health": 5,
            "rarityId": 1, "cardSetId": 1637, "collectible": 1,
            "flavorText": "He always wanted to be a Chillwind Abominable.",
        }],
        "pageCount": 1, "page": 1,
    }
    page1_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.get", return_value=page1_response):
        cards = await client.fetch_cards()

    assert len(cards) == 1
    assert cards[0]["dbf_id"] == 1369
    assert cards[0]["flavor_text"] == "He always wanted to be a Chillwind Abominable."
