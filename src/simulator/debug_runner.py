from __future__ import annotations
import copy
import random
import logging
from src.simulator.game_state import GameState, PlayerState, HeroState
from src.simulator.engine import GameEngine
from src.simulator.event_log import GameEventLog
from src.simulator.ai import SimpleAI
from src.simulator.actions import PlayCard, Attack, HeroPower, EndTurn, TradeCard

logger = logging.getLogger(__name__)


class DebugRunner:
    def __init__(self, deck_a: list[str], deck_b: list[str],
                 hero_a: str, hero_b: str, card_db: dict,
                 max_turns: int = 45, seed: int | None = None):
        if seed is not None:
            random.seed(seed)
        self.card_db = card_db
        self.max_turns = max_turns
        self.engine = GameEngine(card_db=card_db)
        self.log = GameEventLog()
        self.ai = SimpleAI()
        self.state = GameState(
            player1=PlayerState(hero=HeroState(hero_class=hero_a), deck=list(deck_a)),
            player2=PlayerState(hero=HeroState(hero_class=hero_b), deck=list(deck_b)),
        )
        self.turn_count = 0
        self._history: list[dict] = []

    def setup(self) -> dict:
        self.engine.start_game(self.state)
        self._snapshot("GAME_START")
        return self._status()

    def start_turn(self) -> dict:
        self.engine.start_turn(self.state)
        self.turn_count += 1
        self.log.append(self.turn_count, self.state.current_player_idx, "TURN_START", "system",
                        mana=self.state.current_player.mana)
        self._snapshot(f"TURN_{self.turn_count}_START")
        return self._status()

    def get_actions(self) -> list:
        return self.engine.get_legal_actions(self.state)

    def execute(self, action) -> dict:
        action_desc = self._describe_action(action)
        self.log.append(self.turn_count, self.state.current_player_idx, "ACTION", action_desc)

        if isinstance(action, PlayCard):
            player = self.state.current_player
            if action.hand_idx < len(player.hand):
                card_id = player.hand.pop(action.hand_idx)
                card_data = self.card_db.get(card_id, {})
                ct = card_data.get("card_type", "MINION")
                if ct == "MINION":
                    self.engine.play_minion(self.state, card_data)
                    self.log.append(self.turn_count, self.state.current_player_idx, "PLAY_MINION",
                                    card_id, name=card_data.get("name", ""))
                elif ct == "SPELL":
                    self.engine.play_spell(self.state, card_data)
                    self.log.append(self.turn_count, self.state.current_player_idx, "PLAY_SPELL", card_id)
                elif ct == "WEAPON":
                    from src.simulator.game_state import WeaponState
                    player.hero.weapon = WeaponState(
                        card_id=card_data.get("card_id", ""), name=card_data.get("name", ""),
                        attack=card_data.get("attack", 0), durability=card_data.get("durability", 1))
                    player.mana -= card_data.get("mana_cost", 0)
                    self.log.append(self.turn_count, self.state.current_player_idx, "PLAY_WEAPON", card_id)

        elif isinstance(action, Attack):
            player = self.state.current_player
            opponent = self.state.opponent
            if action.attacker_idx == -1:
                if action.target_is_hero:
                    self.engine.hero_attack_hero(self.state)
                    self.log.append(self.turn_count, self.state.current_player_idx, "HERO_ATTACK_HERO", "hero")
                elif action.target_idx < len(opponent.board):
                    target = opponent.board[action.target_idx]
                    self.engine.hero_attack_minion(self.state, target)
                    self.log.append(self.turn_count, self.state.current_player_idx, "HERO_ATTACK_MINION", "hero", target=target.name)
            elif action.attacker_idx < len(player.board):
                attacker = player.board[action.attacker_idx]
                if action.target_is_hero:
                    self.engine.attack_hero(attacker, opponent.hero)
                    self.log.append(self.turn_count, self.state.current_player_idx, "ATTACK_HERO", attacker.name)
                elif action.target_idx < len(opponent.board):
                    defender = opponent.board[action.target_idx]
                    self.engine.resolve_combat(attacker, defender, state=self.state)
                    self.log.append(self.turn_count, self.state.current_player_idx, "COMBAT",
                                    attacker.name, target=defender.name)

        elif isinstance(action, TradeCard):
            player = self.state.current_player
            if action.hand_idx < len(player.hand) and player.mana >= 1 and player.deck:
                card_id = player.hand.pop(action.hand_idx)
                player.deck.append(card_id)
                import random as _rand
                _rand.shuffle(player.deck)
                player.draw_card()
                player.mana -= 1
                self.log.append(self.turn_count, self.state.current_player_idx, "TRADE_CARD", card_id)

        elif isinstance(action, HeroPower):
            self.engine.use_hero_power(self.state)
            self.log.append(self.turn_count, self.state.current_player_idx, "HERO_POWER", "hero")

        self.engine.remove_dead_minions(self.state)
        return self._status()

    def end_turn(self) -> dict:
        self.engine.end_turn(self.state)
        self.log.append(self.turn_count, self.state.current_player_idx, "TURN_END", "system")
        self._snapshot(f"TURN_{self.turn_count}_END")
        return self._status()

    def auto_turn(self) -> dict:
        self.start_turn()
        action_count = 0
        while action_count < 50 and not self.state.game_over:
            action = self.ai.choose_action(self.state, self.engine)
            if isinstance(action, EndTurn):
                break
            self.execute(action)
            if self.state.game_over:
                break
            action_count += 1
        if not self.state.game_over:
            self.end_turn()
        return self._status()

    def run_game(self) -> dict:
        self.setup()
        while not self.state.game_over and self.turn_count < self.max_turns:
            self.auto_turn()
        winner = None
        if self.state.game_over:
            idx = self.state.winner_idx
            if idx == 0: winner = "A"
            elif idx == 1: winner = "B"
        return {"winner": winner, "turns": self.turn_count, "log": self.log.format_all(),
                "events": self.log.to_dicts()}

    def format_board(self) -> str:
        lines = []
        for i, label in [(0, "Player 1"), (1, "Player 2")]:
            p = self.state.player1 if i == 0 else self.state.player2
            h = p.hero
            weapon = f" W:{h.weapon.attack}/{h.weapon.durability}" if h.weapon else ""
            lines.append(f"--- {label} ({h.hero_class}) HP:{h.health} Armor:{h.armor} Mana:{p.mana}/{p.max_mana}{weapon} ---")
            lines.append(f"  Hand: {len(p.hand)} cards | Deck: {len(p.deck)} cards")
            if p.board:
                board_str = "  Board: " + " | ".join(
                    f"[{m.name} {m.attack}/{m.health}" +
                    (" T" if m.taunt else "") + (" DS" if m.divine_shield else "") +
                    (" S" if m.stealth else "") + (" F" if m.frozen else "") +
                    (" P" if m.poisonous else "") + (" R" if m.reborn else "") +
                    "]"
                    for m in p.board
                )
                lines.append(board_str)
            else:
                lines.append("  Board: (empty)")
        return "\n".join(lines)

    def _describe_action(self, action) -> str:
        if isinstance(action, PlayCard):
            card = self.card_db.get(action.card_id, {})
            return f"Play {card.get('name', action.card_id)} (cost {card.get('mana_cost', '?')})"
        if isinstance(action, Attack):
            if action.attacker_idx == -1:
                src = "Hero"
            else:
                p = self.state.current_player
                src = p.board[action.attacker_idx].name if action.attacker_idx < len(p.board) else "?"
            if action.target_is_hero:
                return f"{src} attacks enemy Hero"
            else:
                opp = self.state.opponent
                tgt = opp.board[action.target_idx].name if action.target_idx < len(opp.board) else "?"
                return f"{src} attacks {tgt}"
        if isinstance(action, HeroPower):
            return "Use Hero Power"
        return "End Turn"

    def _snapshot(self, label: str):
        self._history.append({"label": label, "state": self.state.to_dict()})

    def _status(self) -> dict:
        return {
            "turn": self.turn_count,
            "game_over": self.state.game_over,
            "winner": self.state.winner_idx,
            "board": self.format_board(),
        }
