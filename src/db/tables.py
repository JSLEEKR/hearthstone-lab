from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey,
    Index, Integer, JSON, String, Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    card_id = Column(String, unique=True, nullable=False, index=True)
    dbf_id = Column(Integer, unique=True, nullable=False)
    name = Column(String, nullable=False)
    name_ko = Column(String, nullable=False)
    card_type = Column(String, nullable=False)
    hero_class = Column(String, nullable=False)
    mana_cost = Column(Integer, nullable=False)
    attack = Column(Integer, nullable=True)
    health = Column(Integer, nullable=True)
    durability = Column(Integer, nullable=True)
    text = Column(Text, default="")
    rarity = Column(String, nullable=False)
    set_name = Column(String, nullable=False)
    mechanics = Column(JSON, default=list)
    collectible = Column(Boolean, default=True)
    is_standard = Column(Boolean, default=False)
    json_data = Column(JSON, nullable=True)
    image_url = Column(String, default="")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_cards_class_cost", "hero_class", "mana_cost"),
    )


class Deck(Base):
    __tablename__ = "decks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hero_class = Column(String, nullable=False)
    name = Column(String, nullable=False)
    archetype = Column(String, nullable=True)
    format = Column(String, nullable=False)
    deckstring = Column(String, nullable=True)
    source = Column(String, nullable=False, default="manual")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    cards = relationship("DeckCard", back_populates="deck")


class DeckCard(Base):
    __tablename__ = "deck_cards"

    deck_id = Column(Integer, ForeignKey("decks.id"), primary_key=True)
    card_id = Column(Integer, ForeignKey("cards.id"), primary_key=True)
    count = Column(Integer, nullable=False)

    deck = relationship("Deck", back_populates="cards")
    card = relationship("Card")

    __table_args__ = (
        CheckConstraint("count >= 1 AND count <= 2", name="ck_deck_cards_count"),
        Index("ix_deck_cards_card_id", "card_id"),
    )


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deck_a_id = Column(Integer, ForeignKey("decks.id"), nullable=False)
    deck_b_id = Column(Integer, ForeignKey("decks.id"), nullable=False)
    winner_id = Column(Integer, ForeignKey("decks.id"), nullable=True)
    turns = Column(Integer, nullable=False)
    played_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    deck_a = relationship("Deck", foreign_keys=[deck_a_id])
    deck_b = relationship("Deck", foreign_keys=[deck_b_id])
    winner = relationship("Deck", foreign_keys=[winner_id])

    __table_args__ = (
        Index("ix_simulations_deck_a", "deck_a_id"),
        Index("ix_simulations_deck_b", "deck_b_id"),
    )


class HSReplayStats(Base):
    __tablename__ = "hsreplay_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deck_id = Column(Integer, ForeignKey("decks.id"), nullable=False)
    winrate = Column(Float, nullable=False)
    playrate = Column(Float, nullable=False)
    games_played = Column(Integer, nullable=False)
    collected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    deck = relationship("Deck")

    __table_args__ = (
        Index("ix_hsreplay_stats_deck_date", "deck_id", "collected_at"),
    )


class TierHistory(Base):
    __tablename__ = "tier_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deck_id = Column(Integer, ForeignKey("decks.id"), nullable=False)
    tier = Column(String, nullable=False)
    sim_winrate = Column(Float, nullable=True)
    hsreplay_winrate = Column(Float, nullable=True)
    combined_winrate = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    deck = relationship("Deck")

    __table_args__ = (
        Index("ix_tier_history_deck_date", "deck_id", "recorded_at"),
    )
