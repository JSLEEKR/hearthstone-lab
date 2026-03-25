import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import Session, sessionmaker

from src.db.tables import Base, Card, Deck, DeckCard
from src.web.app import create_app
from src.db.database import get_db


@pytest.fixture
def web_app():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    # Seed data
    db = TestSession()
    for i in range(10):
        db.add(Card(
            card_id=f"card_{i}", dbf_id=100+i, name=f"Card {i}",
            name_ko=f"카드 {i}", card_type="MINION", hero_class="NEUTRAL",
            mana_cost=i % 8 + 1, attack=i % 5 + 1, health=i % 5 + 1,
            rarity="COMMON" if i < 8 else "LEGENDARY",
            set_name="TEST", collectible=True, is_standard=True, mechanics=[]
        ))
    db.commit()
    db.close()

    client = TestClient(app)
    yield client, TestSession


class TestPages:
    def test_home_page(self, web_app):
        client, _ = web_app
        response = client.get("/")
        assert response.status_code == 200

    def test_cards_page(self, web_app):
        client, _ = web_app
        response = client.get("/cards")
        assert response.status_code == 200

    def test_builder_page(self, web_app):
        client, _ = web_app
        response = client.get("/builder")
        assert response.status_code == 200

    def test_simulation_page(self, web_app):
        client, _ = web_app
        response = client.get("/simulation")
        assert response.status_code == 200

    def test_deck_not_found(self, web_app):
        client, _ = web_app
        response = client.get("/deck/9999")
        assert response.status_code == 404


class TestAPI:
    def test_search_cards(self, web_app):
        client, _ = web_app
        response = client.get("/api/cards")
        assert response.status_code == 200
        data = response.json()
        assert "cards" in data
        assert len(data["cards"]) > 0

    def test_search_cards_by_name(self, web_app):
        client, _ = web_app
        response = client.get("/api/cards?q=Card 1")
        data = response.json()
        assert any("Card 1" in c["name"] for c in data["cards"])

    def test_create_deck(self, web_app):
        client, _ = web_app
        response = client.post("/api/deck/create?name=TestDeck&hero_class=MAGE")
        data = response.json()
        assert data["deck_id"] is not None

    def test_add_and_remove_card(self, web_app):
        client, _ = web_app
        # Create deck
        res = client.post("/api/deck/create?name=Test&hero_class=MAGE")
        deck_id = res.json()["deck_id"]

        # Add card
        res = client.post(f"/api/deck/add-card?deck_id={deck_id}&card_id=card_0")
        assert res.json()["success"] is True

        # Remove card
        res = client.post(f"/api/deck/remove-card?deck_id={deck_id}&card_id=card_0")
        assert res.json()["success"] is True

    def test_ai_recommend(self, web_app):
        client, _ = web_app
        response = client.post("/api/deck/ai-recommend?hero_class=MAGE")
        assert response.status_code == 200
        data = response.json()
        assert "cards" in data
