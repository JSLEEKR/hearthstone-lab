"""Board state evaluation for AI decision-making."""
from src.simulator.game_state import GameState, MinionState

W_HERO_HP = 1.2
W_ARMOR = 1.0
W_BOARD_ATK = 2.0
W_BOARD_HP = 1.2
W_TAUNT = 3.0
W_DIVINE_SHIELD = 2.0
W_HAND = 1.5
W_LETHAL = 1000.0

def _minion_value(m: MinionState) -> float:
    val = m.attack * W_BOARD_ATK + m.health * W_BOARD_HP
    if m.taunt: val += W_TAUNT
    if m.divine_shield: val += W_DIVINE_SHIELD
    if m.poisonous: val += 4.0
    if m.lifesteal: val += 2.0
    if m.windfury: val += m.attack * 1.5
    if m.stealth: val += 1.5
    if m.reborn: val += 2.0
    return val

def evaluate_state(state: GameState, player_idx: int) -> float:
    me = state.player1 if player_idx == 0 else state.player2
    opp = state.player2 if player_idx == 0 else state.player1

    if opp.hero.is_dead:
        return W_LETHAL
    if me.hero.is_dead:
        return -W_LETHAL

    score = 0.0
    score += (me.hero.health + me.hero.armor) * W_HERO_HP
    score -= (opp.hero.health + opp.hero.armor) * W_HERO_HP
    score += sum(_minion_value(m) for m in me.board)
    score -= sum(_minion_value(m) for m in opp.board)
    score += len(me.hand) * W_HAND
    score -= len(opp.hand) * W_HAND
    return score
