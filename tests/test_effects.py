from src.simulator.effects import EffectRegistry, EventType
from src.simulator.game_state import GameState, PlayerState, HeroState


def _make_state():
    return GameState(
        player1=PlayerState(hero=HeroState(hero_class="MAGE")),
        player2=PlayerState(hero=HeroState(hero_class="WARRIOR")),
    )


class TestEffectRegistry:
    def test_register_and_trigger(self):
        registry = EffectRegistry()
        triggered = []
        registry.register("TEST_CARD", EventType.ON_PLAY, lambda s, c: triggered.append(c["card_id"]))
        registry.trigger(EventType.ON_PLAY, _make_state(), {"card_id": "TEST_CARD"})
        assert triggered == ["TEST_CARD"]

    def test_unregistered_card_no_effect(self):
        registry = EffectRegistry()
        registry.trigger(EventType.ON_PLAY, _make_state(), {"card_id": "UNKNOWN"})

    def test_multiple_effects(self):
        registry = EffectRegistry()
        results = []
        registry.register("CARD_A", EventType.ON_PLAY, lambda s, c: results.append("A"))
        registry.register("CARD_B", EventType.ON_PLAY, lambda s, c: results.append("B"))
        state = _make_state()
        registry.trigger(EventType.ON_PLAY, state, {"card_id": "CARD_A"})
        registry.trigger(EventType.ON_PLAY, state, {"card_id": "CARD_B"})
        assert results == ["A", "B"]

    def test_global_event(self):
        registry = EffectRegistry()
        triggered = []
        registry.register_global(EventType.ON_TURN_START, lambda s, c: triggered.append("global"))
        registry.trigger_global(EventType.ON_TURN_START, _make_state(), {})
        assert triggered == ["global"]
