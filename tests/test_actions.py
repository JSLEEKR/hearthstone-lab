from src.simulator.actions import PlayCard, Attack, HeroPower, EndTurn, ActionType


def test_play_card_action():
    a = PlayCard(card_id="CS2_029", hand_idx=0)
    assert a.action_type == ActionType.PLAY_CARD

def test_attack_action():
    a = Attack(attacker_idx=0, target_idx=1, target_is_hero=False)
    assert a.action_type == ActionType.ATTACK

def test_hero_power_action():
    a = HeroPower()
    assert a.action_type == ActionType.HERO_POWER

def test_end_turn_action():
    a = EndTurn()
    assert a.action_type == ActionType.END_TURN
