"""Track live Hearthstone game state from Power.log events."""
from __future__ import annotations
from dataclasses import dataclass, field
from helper.log_watcher import GameEvent


@dataclass
class TrackedCard:
    entity_id: int
    card_id: str
    card_name: str
    zone: str = ""  # HAND, PLAY, DECK, GRAVEYARD, SECRET
    player: int = 0
    cost: int = 0
    attack: int = 0
    health: int = 0
    card_type: str = ""


@dataclass
class LiveGameState:
    """Current game state derived from Power.log events."""
    in_game: bool = False
    turn: int = 0
    my_player_id: int = 1  # Which player am I (1 or 2)

    # My state
    my_hand: list[TrackedCard] = field(default_factory=list)
    my_board: list[TrackedCard] = field(default_factory=list)
    my_deck_remaining: int = 30
    my_hero_health: int = 30
    my_mana: int = 0
    my_secrets: list[TrackedCard] = field(default_factory=list)
    my_weapon: TrackedCard | None = None

    # Opponent state
    opp_hand_count: int = 0
    opp_board: list[TrackedCard] = field(default_factory=list)
    opp_deck_remaining: int = 30
    opp_hero_health: int = 30
    opp_played_cards: list[TrackedCard] = field(default_factory=list)
    opp_secrets_count: int = 0

    # History
    cards_played_this_game: list[TrackedCard] = field(default_factory=list)
    events_log: list[str] = field(default_factory=list)


class GameTracker:
    """Process GameEvents into a LiveGameState."""

    def __init__(self, card_db: dict | None = None):
        self.state = LiveGameState()
        self.entities: dict[int, TrackedCard] = {}
        self.card_db = card_db or {}

    def process_event(self, event: GameEvent):
        """Update state based on a game event."""
        handler = getattr(self, f"_on_{event.event_type.lower()}", None)
        if handler:
            handler(event)

    def _on_game_start(self, event: GameEvent):
        self.state = LiveGameState(in_game=True)
        self.entities.clear()
        self.state.events_log.append("Game started")

    def _on_turn(self, event: GameEvent):
        turn = int(event.tags.get("TURN", 0))
        self.state.turn = turn
        self.state.events_log.append(f"Turn {turn}")

    def _on_entity_create(self, event: GameEvent):
        card = TrackedCard(
            entity_id=event.entity_id,
            card_id=event.card_id,
            card_name=event.card_name,
            player=event.player,
        )
        # Enrich from card_db
        if event.card_id and event.card_id in self.card_db:
            db_card = self.card_db[event.card_id]
            card.card_name = card.card_name or db_card.get("name", "")
            card.cost = db_card.get("mana_cost", 0)
            card.attack = db_card.get("attack", 0)
            card.health = db_card.get("health", 0)
            card.card_type = db_card.get("card_type", "")
        self.entities[event.entity_id] = card

    def _on_card_drawn(self, event: GameEvent):
        card = self.entities.get(event.entity_id)
        if card:
            card.zone = "HAND"
            if event.player == self.state.my_player_id:
                if card not in self.state.my_hand:
                    self.state.my_hand.append(card)
                self.state.my_deck_remaining = max(0, self.state.my_deck_remaining - 1)
                self.state.events_log.append(f"Drew: {card.card_name or '???'}")
            else:
                self.state.opp_hand_count += 1
                self.state.opp_deck_remaining = max(0, self.state.opp_deck_remaining - 1)
                self.state.events_log.append("Opponent drew a card")

    def _on_card_played(self, event: GameEvent):
        card = self.entities.get(event.entity_id)
        if not card:
            card = TrackedCard(entity_id=event.entity_id, card_id=event.card_id,
                               card_name=event.card_name, player=event.player)
        card.zone = "PLAY"

        if event.player == self.state.my_player_id:
            if card in self.state.my_hand:
                self.state.my_hand.remove(card)
            if card.card_type in ("MINION", "LOCATION"):
                self.state.my_board.append(card)
            self.state.events_log.append(f"Played: {card.card_name or card.card_id}")
        else:
            self.state.opp_hand_count = max(0, self.state.opp_hand_count - 1)
            if card.card_type in ("MINION", "LOCATION"):
                self.state.opp_board.append(card)
            self.state.opp_played_cards.append(card)
            self.state.events_log.append(f"Opponent played: {card.card_name or card.card_id}")

        self.state.cards_played_this_game.append(card)

    def _on_card_died(self, event: GameEvent):
        card = self.entities.get(event.entity_id)
        if card:
            card.zone = "GRAVEYARD"
            if event.player == self.state.my_player_id:
                if card in self.state.my_board:
                    self.state.my_board.remove(card)
            else:
                if card in self.state.opp_board:
                    self.state.opp_board.remove(card)
            self.state.events_log.append(f"Died: {card.card_name or card.card_id}")

    def _on_card_revealed(self, event: GameEvent):
        # Opponent's card revealed (e.g., played from hand)
        card = self.entities.get(event.entity_id)
        if card:
            card.card_id = event.card_id
            if event.card_id in self.card_db:
                db = self.card_db[event.card_id]
                card.card_name = db.get("name", "")
                card.cost = db.get("mana_cost", 0)

    def _on_game_end(self, event: GameEvent):
        result = event.tags.get("PLAYSTATE", "")
        self.state.in_game = False
        self.state.events_log.append(f"Game Over: Player {event.player} {result}")

    def _on_block_start(self, event: GameEvent):
        if event.block_type == "ATTACK":
            attacker = self.entities.get(event.entity_id)
            target = self.entities.get(event.target_id)
            a_name = attacker.card_name if attacker else "?"
            t_name = target.card_name if target else "Hero"
            self.state.events_log.append(f"Attack: {a_name} -> {t_name}")

    def _on_zone_change(self, event: GameEvent):
        # Generic zone change fallback
        pass

    def _on_tag_set(self, event: GameEvent):
        # Update entity tags
        card = self.entities.get(event.entity_id)
        if card:
            for tag, val in event.tags.items():
                if tag == "ATK":
                    card.attack = int(val) if val.isdigit() else 0
                elif tag == "HEALTH":
                    card.health = int(val) if val.isdigit() else 0
                elif tag == "COST":
                    card.cost = int(val) if val.isdigit() else 0
