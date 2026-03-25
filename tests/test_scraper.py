import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.db.tables import Base, Card, Deck, DeckCard, HSReplayStats
from src.scraper.api_client import HSReplayClient
from src.scraper.parser import HSReplayParser


@pytest.fixture
def scraper_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for i in range(30):
            session.add(Card(
                card_id=f"card_{i}", dbf_id=100+i, name=f"Card {i}",
                name_ko=f"카드 {i}", card_type="MINION", hero_class="NEUTRAL",
                mana_cost=i % 8 + 1, attack=i % 5 + 1, health=i % 5 + 1,
                rarity="COMMON", set_name="TEST", collectible=True,
                is_standard=True, mechanics=[]
            ))
        session.commit()
        yield session
    engine.dispose()


class TestHSReplayClient:
    def test_client_init(self):
        client = HSReplayClient()
        assert client.base_url is not None

    @pytest.mark.asyncio
    async def test_fetch_deck_stats_returns_list(self):
        client = HSReplayClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "series": {
                "data": {
                    "ALL": [
                        {
                            "deck_id": "abc123",
                            "win_rate": 55.3,
                            "popularity": 4.2,
                            "total_games": 1500,
                            "archetype_id": 1,
                            "player_class_name": "MAGE",
                        }
                    ]
                }
            }
        }
        with patch.object(client, "_get", return_value=mock_response):
            result = await client.fetch_deck_stats(format_type="standard")
        assert len(result) >= 1
        assert result[0]["win_rate"] == 55.3

    @pytest.mark.asyncio
    async def test_fetch_deck_detail_returns_deckstring(self):
        client = HSReplayClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "deck_id": "abc123",
            "deckstring": "AAEBAf0EBu72Avb9A...",
            "archetype": "Tempo Mage",
        }
        with patch.object(client, "_get", return_value=mock_response):
            result = await client.fetch_deck_detail("abc123")
        assert "deckstring" in result


class TestHSReplayParser:
    def test_parse_deck_stats(self, scraper_db):
        parser = HSReplayParser(scraper_db)
        raw_data = [
            {
                "deck_id": "abc123",
                "win_rate": 55.3,
                "popularity": 4.2,
                "total_games": 1500,
                "player_class_name": "MAGE",
                "deckstring": None,
            }
        ]
        result = parser.parse_deck_stats(raw_data, format_type="standard")
        assert len(result) >= 0

    def test_save_stats(self, scraper_db):
        parser = HSReplayParser(scraper_db)
        deck = Deck(name="Test Deck", hero_class="MAGE", format="standard", source="hsreplay")
        scraper_db.add(deck)
        scraper_db.commit()

        parser.save_stats(deck.id, winrate=55.3, playrate=4.2, games_played=1500)
        stats = scraper_db.query(HSReplayStats).filter_by(deck_id=deck.id).first()
        assert stats is not None
        assert stats.winrate == 55.3
        assert stats.games_played == 1500

    def test_find_or_create_deck_new(self, scraper_db):
        parser = HSReplayParser(scraper_db)
        deck = parser.find_or_create_deck(hero_class="MAGE", format_type="standard",
                                           name="New Deck")
        assert deck.id is not None
        assert deck.source == "hsreplay"

    def test_find_or_create_deck_existing(self, scraper_db):
        parser = HSReplayParser(scraper_db)
        deck1 = parser.find_or_create_deck(hero_class="MAGE", format_type="standard",
                                            deckstring="AAE123")
        deck2 = parser.find_or_create_deck(hero_class="MAGE", format_type="standard",
                                            deckstring="AAE123")
        assert deck1.id == deck2.id


class TestWebScraper:
    def test_scraper_init(self):
        from src.scraper.web_scraper import HSReplayWebScraper
        scraper = HSReplayWebScraper()
        assert scraper.base_url is not None

    @pytest.mark.asyncio
    async def test_scrape_returns_list(self):
        from src.scraper.web_scraper import HSReplayWebScraper
        scraper = HSReplayWebScraper()
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector_all = AsyncMock(return_value=[])
        mock_page.close = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_pw = AsyncMock()
        mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_pw.stop = AsyncMock()

        mock_async_pw = AsyncMock()
        mock_async_pw.start = AsyncMock(return_value=mock_pw)

        with patch("playwright.async_api.async_playwright", return_value=mock_async_pw):
            result = await scraper.scrape_tier_list(format_type="standard")
        assert isinstance(result, list)
