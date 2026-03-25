from src.simulator.event_log import GameEventLog


class TestEventLog:
    def test_append_and_retrieve(self):
        log = GameEventLog()
        log.append(1, 0, "DRAW", "card_1")
        log.append(1, 0, "PLAY_MINION", "card_1")
        assert len(log.events) == 2

    def test_get_turn(self):
        log = GameEventLog()
        log.append(1, 0, "DRAW", "card_1")
        log.append(2, 1, "ATTACK", "minion_1", target="hero")
        turn1 = log.get_turn(1)
        assert len(turn1) == 1

    def test_format_event(self):
        log = GameEventLog()
        log.append(1, 0, "DAMAGE", "fireball", target="yeti", damage=6)
        text = log.format_event(log.events[0])
        assert "DAMAGE" in text
        assert "fireball" in text

    def test_to_dicts(self):
        log = GameEventLog()
        log.append(1, 0, "DRAW", "card_1")
        dicts = log.to_dicts()
        assert len(dicts) == 1
        assert dicts[0]["type"] == "DRAW"
