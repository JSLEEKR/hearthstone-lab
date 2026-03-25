"""Tests for expansion-specific keywords: spell power, combo, echo, miniaturize, tradeable, secret."""
import pytest
from src.simulator.game_state import GameState, PlayerState, HeroState, MinionState
from src.simulator.engine import GameEngine
from src.simulator.actions import PlayCard, TradeCard


class TestSpellPower:
    def test_spell_power_adds_damage(self):
        engine = GameEngine(card_db={})
        state = GameState(
            player1=PlayerState(hero=HeroState(hero_class="MAGE"), mana=10, max_mana=10),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        # Add spell power minion to board
        state.player1.board.append(MinionState(
            card_id="sp", name="SP", attack=1, health=1, max_health=1,
            mana_cost=1, mechanics=["SPELLPOWER"],
        ))
        # Cast damage spell: base 6 + 1 spell power = 7
        engine.play_spell(state, {"mana_cost": 4, "text": "피해를 6 줍니다.", "mechanics": []})
        assert state.player2.hero.health == 23  # 30 - 7

    def test_spell_power_stacks(self):
        engine = GameEngine(card_db={})
        state = GameState(
            player1=PlayerState(hero=HeroState(hero_class="MAGE"), mana=10, max_mana=10),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        # Add two spell power minions
        for _ in range(2):
            state.player1.board.append(MinionState(
                card_id="sp", name="SP", attack=1, health=1, max_health=1,
                mana_cost=1, mechanics=["SPELLPOWER"],
            ))
        engine.play_spell(state, {"mana_cost": 4, "text": "피해를 6 줍니다.", "mechanics": []})
        assert state.player2.hero.health == 22  # 30 - 8

    def test_spell_power_no_effect_on_heal(self):
        engine = GameEngine(card_db={})
        state = GameState(
            player1=PlayerState(hero=HeroState(hero_class="PRIEST", health=20, max_health=30), mana=10, max_mana=10),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        state.player1.board.append(MinionState(
            card_id="sp", name="SP", attack=1, health=1, max_health=1,
            mana_cost=1, mechanics=["SPELLPOWER"],
        ))
        engine.play_spell(state, {"mana_cost": 2, "text": "체력을 5 회복합니다", "mechanics": []})
        assert state.player1.hero.health == 25  # heal is not boosted by spell power

    def test_get_spell_power_empty_board(self):
        engine = GameEngine(card_db={})
        state = GameState(
            player1=PlayerState(hero=HeroState(hero_class="MAGE")),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        assert engine._get_spell_power(state) == 0


class TestCombo:
    def test_combo_not_triggered_first_card(self):
        engine = GameEngine(card_db={})
        state = GameState(
            player1=PlayerState(hero=HeroState(hero_class="ROGUE"), mana=10, max_mana=10),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        state.player1.cards_played_this_turn = 0
        engine.play_minion(state, {
            "card_id": "combo1", "mana_cost": 2, "attack": 2, "health": 2,
            "name": "Combo", "mechanics": ["COMBO"],
            "text": "<b>연계:</b> 피해를 3 줍니다.",
        })
        assert state.player2.hero.health == 30

    def test_combo_triggered_after_another_card(self):
        engine = GameEngine(card_db={})
        state = GameState(
            player1=PlayerState(hero=HeroState(hero_class="ROGUE"), mana=10, max_mana=10),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        state.player1.cards_played_this_turn = 1  # already played a card
        engine.play_minion(state, {
            "card_id": "combo1", "mana_cost": 2, "attack": 2, "health": 2,
            "name": "Combo", "mechanics": ["COMBO"],
            "text": "<b>연계:</b> 피해를 3 줍니다.",
        })
        assert state.player2.hero.health == 27

    def test_combo_increments_cards_played(self):
        engine = GameEngine(card_db={})
        state = GameState(
            player1=PlayerState(hero=HeroState(hero_class="ROGUE"), mana=10, max_mana=10),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        assert state.player1.cards_played_this_turn == 0
        engine.play_minion(state, {
            "card_id": "m1", "mana_cost": 1, "attack": 1, "health": 1,
            "name": "Basic", "mechanics": [], "text": "",
        })
        assert state.player1.cards_played_this_turn == 1


class TestEcho:
    def test_echo_adds_copy_to_hand(self):
        engine = GameEngine(card_db={})
        state = GameState(
            player1=PlayerState(hero=HeroState(hero_class="SHAMAN"), mana=10, max_mana=10, hand=["echo1"]),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        # Remove from hand (simulating the card being played from hand)
        state.player1.hand.pop(0)
        engine.play_minion(state, {
            "card_id": "echo1", "mana_cost": 2, "attack": 1, "health": 1,
            "name": "Echo", "mechanics": ["ECHO"], "text": "",
        })
        assert "echo1" in state.player1.hand  # copy added back
        assert "echo1" in state.player1.echo_cards

    def test_echo_copies_removed_end_turn(self):
        engine = GameEngine(card_db={})
        state = GameState(
            player1=PlayerState(
                hero=HeroState(hero_class="SHAMAN"), mana=10, max_mana=10,
                hand=["echo1", "other"],
                echo_cards=["echo1"],
            ),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        engine.end_turn(state)
        assert "echo1" not in state.player1.hand
        assert "other" in state.player1.hand
        assert len(state.player1.echo_cards) == 0


class TestMiniaturize:
    def test_miniaturize_summons_copy(self):
        engine = GameEngine(card_db={})
        state = GameState(
            player1=PlayerState(hero=HeroState(hero_class="MAGE"), mana=10, max_mana=10),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        engine.play_minion(state, {
            "card_id": "mini1", "mana_cost": 5, "attack": 5, "health": 5,
            "name": "Big Guy", "mechanics": ["MINIATURIZE"], "text": "",
        })
        assert len(state.player1.board) == 2  # original + 1/1 copy
        assert state.player1.board[0].attack == 5
        assert state.player1.board[0].health == 5
        assert state.player1.board[1].attack == 1
        assert state.player1.board[1].health == 1
        assert "(Mini)" in state.player1.board[1].name

    def test_miniaturize_no_copy_if_board_full(self):
        engine = GameEngine(card_db={})
        state = GameState(
            player1=PlayerState(hero=HeroState(hero_class="MAGE"), mana=10, max_mana=10),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        # Fill board to 6 so playing miniaturize makes 7 (full), no room for mini
        for i in range(6):
            state.player1.board.append(MinionState(
                card_id=f"f{i}", name=f"Filler{i}", attack=1, health=1,
                max_health=1, mana_cost=1,
            ))
        engine.play_minion(state, {
            "card_id": "mini1", "mana_cost": 5, "attack": 5, "health": 5,
            "name": "Big Guy", "mechanics": ["MINIATURIZE"], "text": "",
        })
        assert len(state.player1.board) == 7  # no mini copy since board is full


class TestTradeable:
    def test_trade_card_action_available(self):
        engine = GameEngine(card_db={
            "trade1": {
                "card_id": "trade1", "card_type": "MINION", "mana_cost": 5,
                "mechanics": ["TRADEABLE"], "name": "Trade",
            },
        })
        state = GameState(
            player1=PlayerState(
                hero=HeroState(hero_class="MAGE"), mana=3, max_mana=3,
                hand=["trade1"], deck=["other1", "other2"],
            ),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        actions = engine.get_legal_actions(state)
        trade_actions = [a for a in actions if isinstance(a, TradeCard)]
        # Trade should be available (costs 1 mana, player has 3)
        assert len(trade_actions) == 1
        assert trade_actions[0].card_id == "trade1"
        # But PlayCard should NOT be available (card costs 5 mana, player has 3)
        play_actions = [a for a in actions if isinstance(a, PlayCard)]
        assert len(play_actions) == 0

    def test_trade_card_not_available_no_deck(self):
        engine = GameEngine(card_db={
            "trade1": {
                "card_id": "trade1", "card_type": "MINION", "mana_cost": 2,
                "mechanics": ["TRADEABLE"], "name": "Trade",
            },
        })
        state = GameState(
            player1=PlayerState(
                hero=HeroState(hero_class="MAGE"), mana=3, max_mana=3,
                hand=["trade1"], deck=[],
            ),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        actions = engine.get_legal_actions(state)
        trade_actions = [a for a in actions if isinstance(a, TradeCard)]
        assert len(trade_actions) == 0


class TestSecret:
    def test_secret_added_to_list(self):
        engine = GameEngine(card_db={})
        state = GameState(
            player1=PlayerState(hero=HeroState(hero_class="MAGE"), mana=10, max_mana=10),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        engine.play_spell(state, {
            "card_id": "secret1", "mana_cost": 3,
            "mechanics": ["SECRET"],
            "text": "비밀: 적 하수인이 소환될 때 파괴합니다.",
        })
        assert "secret1" in state.player1.secrets
        # Should not deal any damage (effect not resolved)
        assert state.player2.hero.health == 30

    def test_secret_increments_cards_played(self):
        engine = GameEngine(card_db={})
        state = GameState(
            player1=PlayerState(hero=HeroState(hero_class="MAGE"), mana=10, max_mana=10),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        engine.play_spell(state, {
            "card_id": "secret1", "mana_cost": 3,
            "mechanics": ["SECRET"],
            "text": "비밀: 적 하수인이 소환될 때 파괴합니다.",
        })
        assert state.player1.cards_played_this_turn == 1


class TestCardsPlayedCounter:
    def test_start_turn_resets_counter(self):
        engine = GameEngine(card_db={})
        state = GameState(
            player1=PlayerState(
                hero=HeroState(hero_class="ROGUE"), mana=5, max_mana=5,
                cards_played_this_turn=3, deck=["a"],
            ),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        engine.start_turn(state)
        assert state.player1.cards_played_this_turn == 0

    def test_spell_increments_counter(self):
        engine = GameEngine(card_db={})
        state = GameState(
            player1=PlayerState(hero=HeroState(hero_class="MAGE"), mana=10, max_mana=10),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        engine.play_spell(state, {"mana_cost": 1, "text": "", "mechanics": []})
        assert state.player1.cards_played_this_turn == 1

    def test_minion_increments_counter(self):
        engine = GameEngine(card_db={})
        state = GameState(
            player1=PlayerState(hero=HeroState(hero_class="MAGE"), mana=10, max_mana=10),
            player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
        )
        engine.play_minion(state, {
            "card_id": "m1", "mana_cost": 1, "attack": 1, "health": 1,
            "name": "M", "mechanics": [], "text": "",
        })
        assert state.player1.cards_played_this_turn == 1


class TestSpellParserCombo:
    def test_parse_combo_effects(self):
        from src.simulator.spell_parser import parse_combo_effects
        effects = parse_combo_effects("<b>연계:</b> 피해를 3 줍니다.")
        assert len(effects) == 1
        assert effects[0].effect_type == "damage"
        assert effects[0].value == 3

    def test_parse_combo_no_combo_text(self):
        from src.simulator.spell_parser import parse_combo_effects
        effects = parse_combo_effects("전투의 함성: 카드를 뽑습니다.")
        assert len(effects) == 0
