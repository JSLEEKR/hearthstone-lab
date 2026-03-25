# AI + Tournament System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 3-level AI system (Rule-based → Score-based → MCTS) and a round-robin tournament simulator with statistical output for comparing 5+ decks.

**Architecture:** Three AI classes sharing the same interface (`choose_action`, `mulligan`). A `Tournament` class runs round-robin matchups between all deck pairs, collects per-matchup win rates, and outputs a summary matrix + overall rankings. The `match.py` module is extended to accept any AI instance.

**Tech Stack:** Python dataclasses, copy.deepcopy for state simulation, math/statistics for MCTS UCB1, tabulate-style text output for results.

---

## File Structure

| File | Responsibility |
|------|---------------|
| `src/simulator/ai.py` | All 3 AI levels: `RuleBasedAI`, `ScoreBasedAI`, `MCTSAI` + shared `BaseAI` |
| `src/simulator/evaluator.py` | Board state evaluation function (used by Level 2 & 3) |
| `src/simulator/match.py` | Extended to accept AI class parameter |
| `src/simulator/tournament.py` | Round-robin tournament runner + statistics |
| `tests/test_ai.py` | AI behavior tests |
| `tests/test_evaluator.py` | Board evaluation tests |
| `tests/test_tournament.py` | Tournament runner tests |
| `src/web/routes/api.py` | Tournament API endpoint |
| `src/web/templates/tournament.html` | Tournament results page |

---

### Task 1: Board State Evaluator

**Files:**
- Create: `src/simulator/evaluator.py`
- Test: `tests/test_evaluator.py`

The evaluator is the brain — it scores a board state from a player's perspective. Used by ScoreBasedAI (1-step lookahead) and MCTSAI (rollout evaluation).

- [ ] **Step 1: Write failing tests for evaluator**

```python
# tests/test_evaluator.py
import pytest
from src.simulator.game_state import GameState, PlayerState, HeroState, MinionState
from src.simulator.evaluator import evaluate_state

def _state(**kw):
    return GameState(
        PlayerState(hero=HeroState("MAGE"), **kw),
        PlayerState(hero=HeroState("WARRIOR")),
    )

class TestEvaluator:
    def test_empty_board_equal(self):
        state = _state()
        score = evaluate_state(state, player_idx=0)
        assert score == pytest.approx(0, abs=5)  # roughly even

    def test_board_advantage(self):
        state = _state()
        state.player1.board = [MinionState("a","A",3,4,4,3)]
        score = evaluate_state(state, player_idx=0)
        assert score > 0  # player 1 has board advantage

    def test_health_matters(self):
        state = _state()
        state.player1.hero.health = 10
        state.player2.hero.health = 30
        score = evaluate_state(state, player_idx=0)
        assert score < 0  # low health is bad

    def test_lethal_is_max(self):
        state = _state()
        state.player2.hero.health = 0
        score = evaluate_state(state, player_idx=0)
        assert score > 900  # winning is very high score

    def test_dead_is_min(self):
        state = _state()
        state.player1.hero.health = 0
        score = evaluate_state(state, player_idx=0)
        assert score < -900

    def test_taunt_bonus(self):
        state = _state()
        m1 = MinionState("t","Taunt",2,5,5,3, taunt=True)
        state.player1.board = [m1]
        score_taunt = evaluate_state(state, player_idx=0)
        m1.taunt = False
        score_no_taunt = evaluate_state(state, player_idx=0)
        assert score_taunt > score_no_taunt

    def test_hand_advantage(self):
        s1 = _state(hand=["a","b","c","d"])
        s2 = _state(hand=["a"])
        assert evaluate_state(s1, 0) > evaluate_state(s2, 0)
```

- [ ] **Step 2: Run tests → FAIL**
- [ ] **Step 3: Implement evaluator**

```python
# src/simulator/evaluator.py
"""Board state evaluation for AI decision-making."""
from src.simulator.game_state import GameState, MinionState

# Weights
W_HERO_HP = 1.0
W_ARMOR = 1.0
W_BOARD_ATK = 2.0
W_BOARD_HP = 1.5
W_TAUNT = 3.0
W_DIVINE_SHIELD = 2.0
W_HAND = 2.0
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
```

- [ ] **Step 4: Run tests → PASS**
- [ ] **Step 5: Commit**

---

### Task 2: BaseAI Interface + RuleBasedAI (Level 1 Improvement)

**Files:**
- Modify: `src/simulator/ai.py`
- Test: `tests/test_ai.py`

Refactor current SimpleAI into proper `RuleBasedAI` with smarter ordering: play cards first (mana curve), then attack (efficient trades), then hero power.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_ai.py
import pytest
from src.simulator.game_state import GameState, PlayerState, HeroState, MinionState
from src.simulator.engine import GameEngine
from src.simulator.ai import RuleBasedAI, ScoreBasedAI
from src.simulator.actions import PlayCard, Attack, EndTurn, HeroPower

def _state(card_db=None, **kw):
    return GameState(
        PlayerState(hero=HeroState("MAGE"), **kw),
        PlayerState(hero=HeroState("WARRIOR")),
    ), GameEngine(card_db or {})

class TestRuleBasedAI:
    def test_plays_cards_before_attacking(self):
        card_db = {"c1": {"card_id":"c1","card_type":"MINION","mana_cost":2,
            "attack":3,"health":2,"mechanics":[],"name":"C1"}}
        state, engine = _state(card_db, mana=5, max_mana=5, hand=["c1"])
        state.player1.board = [MinionState("a","A",2,3,3,2, summoned_this_turn=False)]
        state.player2.board = [MinionState("b","B",1,2,2,1)]
        ai = RuleBasedAI()
        action = ai.choose_action(state, engine)
        assert isinstance(action, PlayCard)  # should play card first

    def test_efficient_trade(self):
        state, engine = _state()
        # 3/2 attacker vs 2/3 target — bad trade (doesn't kill)
        # 3/2 attacker vs 2/2 target — good trade (kills)
        state.player1.board = [MinionState("a","A",3,2,2,2, summoned_this_turn=False)]
        state.player2.board = [
            MinionState("b1","B1",2,3,3,3),  # doesn't die
            MinionState("b2","B2",2,2,2,2),  # dies
        ]
        ai = RuleBasedAI()
        action = ai.choose_action(state, engine)
        if isinstance(action, Attack):
            assert action.target_idx == 1  # should pick the killable target

    def test_mulligan_keeps_low_cost(self):
        card_db = {
            "cheap": {"mana_cost": 2},
            "mid": {"mana_cost": 4},
            "expensive": {"mana_cost": 8},
        }
        ai = RuleBasedAI()
        keep = ai.mulligan(["cheap", "mid", "expensive"], card_db)
        assert "cheap" in keep
        assert "expensive" not in keep
```

- [ ] **Step 2: Run tests → FAIL**
- [ ] **Step 3: Implement RuleBasedAI**

```python
# In src/simulator/ai.py — replace SimpleAI with:

from __future__ import annotations
import copy
import math
import random
from typing import TYPE_CHECKING
from src.simulator.actions import PlayCard, Attack, HeroPower, EndTurn, TradeCard

if TYPE_CHECKING:
    from src.simulator.engine import GameEngine
    from src.simulator.game_state import GameState

MULLIGAN_COST_THRESHOLD = 3


class BaseAI:
    """Common interface for all AI levels."""
    def choose_action(self, state: GameState, engine: GameEngine):
        raise NotImplementedError

    def mulligan(self, hand: list[str], card_db: dict) -> list[str]:
        return [cid for cid in hand
                if card_db.get(cid, {}).get("mana_cost", 99) <= MULLIGAN_COST_THRESHOLD]


class RuleBasedAI(BaseAI):
    """Level 1: Fast rule-based AI. Plays cards first, then trades, then hits face."""

    def choose_action(self, state: GameState, engine: GameEngine):
        actions = engine.get_legal_actions(state)

        # Priority 1: Play cards (highest mana cost that fits curve)
        plays = [a for a in actions if isinstance(a, PlayCard)]
        if plays:
            plays.sort(key=lambda p: engine.card_db.get(p.card_id, {}).get("mana_cost", 0),
                       reverse=True)
            return plays[0]

        # Priority 2: Efficient attacks
        attacks = [a for a in actions if isinstance(a, Attack)]
        if attacks:
            return self._best_attack(attacks, state)

        # Priority 3: Hero power
        hero_powers = [a for a in actions if isinstance(a, HeroPower)]
        if hero_powers:
            return hero_powers[0]

        return EndTurn()

    def _best_attack(self, attacks: list[Attack], state: GameState) -> Attack:
        player = state.current_player
        opponent = state.opponent
        best = None
        best_score = -9999

        for a in attacks:
            if a.attacker_idx == -1:
                atk_value = player.hero.total_attack
                atk_health = 999
            else:
                m = player.board[a.attacker_idx]
                atk_value = m.attack
                atk_health = m.health

            if a.target_is_hero:
                score = atk_value * 1.5  # face damage
            else:
                defender = opponent.board[a.target_idx]
                kills = defender.health <= atk_value
                survives = atk_health > defender.attack
                if kills and survives:
                    score = 100 + defender.mana_cost  # best: kill and live
                elif kills:
                    score = 50 + defender.mana_cost  # trade: both die
                elif defender.taunt:
                    score = 30  # must hit taunt even if inefficient
                else:
                    score = -10  # bad trade, don't do unless nothing else

            if score > best_score:
                best_score = score
                best = a

        return best or attacks[0]
```

- [ ] **Step 4: Run tests → PASS**
- [ ] **Step 5: Commit**

---

### Task 3: ScoreBasedAI (Level 2 — 1-step Lookahead)

**Files:**
- Modify: `src/simulator/ai.py` (add ScoreBasedAI)
- Test: `tests/test_ai.py` (add ScoreBasedAI tests)

Uses `evaluate_state()` with state cloning to test every legal action and pick the best outcome.

- [ ] **Step 1: Write failing test**

```python
class TestScoreBasedAI:
    def test_finds_lethal(self):
        """AI should detect lethal and go face."""
        state, engine = _state(mana=0, max_mana=10)
        # 5-attack minion, enemy at 5 HP
        state.player1.board = [MinionState("a","A",5,3,3,3, summoned_this_turn=False)]
        state.player2.hero.health = 5
        ai = ScoreBasedAI()
        action = ai.choose_action(state, engine)
        assert isinstance(action, Attack)
        assert action.target_is_hero  # must go face for lethal

    def test_prefers_value_trade(self):
        """AI should prefer killing a big threat over going face."""
        state, engine = _state(mana=0, max_mana=10)
        state.player1.board = [MinionState("a","A",5,6,6,5, summoned_this_turn=False)]
        state.player2.board = [MinionState("b","B",8,5,5,8)]  # 8-attack threat
        state.player2.hero.health = 30
        ai = ScoreBasedAI()
        action = ai.choose_action(state, engine)
        assert isinstance(action, Attack)
        assert not action.target_is_hero  # should kill the 8-attack threat
```

- [ ] **Step 2: Run tests → FAIL**
- [ ] **Step 3: Implement ScoreBasedAI**

```python
class ScoreBasedAI(BaseAI):
    """Level 2: Evaluates board state after each possible action, picks highest score."""

    def choose_action(self, state: GameState, engine: GameEngine):
        from src.simulator.evaluator import evaluate_state
        from src.simulator.match import _execute_action

        actions = engine.get_legal_actions(state)
        player_idx = state.current_player_idx

        best_action = EndTurn()
        best_score = evaluate_state(state, player_idx)  # score of doing nothing (EndTurn)

        for action in actions:
            if isinstance(action, EndTurn):
                continue
            try:
                sim_state = copy.deepcopy(state)
                sim_engine = GameEngine(card_db=engine.card_db)
                _execute_action(sim_engine, sim_state, action, engine.card_db)
                sim_engine.remove_dead_minions(sim_state)
                score = evaluate_state(sim_state, player_idx)
                if score > best_score:
                    best_score = score
                    best_action = action
            except Exception:
                continue

        return best_action
```

- [ ] **Step 4: Run tests → PASS**
- [ ] **Step 5: Commit**

---

### Task 4: MCTS AI (Level 3)

**Files:**
- Modify: `src/simulator/ai.py` (add MCTSAI)
- Test: `tests/test_ai.py`

Monte Carlo Tree Search with UCB1 selection. Simulates random rollouts from each candidate action and picks the one with highest average score.

- [ ] **Step 1: Write failing test**

```python
class TestMCTSAI:
    def test_finds_lethal(self):
        state, engine = _state(mana=0, max_mana=10)
        state.player1.board = [MinionState("a","A",7,3,3,3, summoned_this_turn=False)]
        state.player2.hero.health = 5
        ai = MCTSAI(iterations=50)
        action = ai.choose_action(state, engine)
        assert isinstance(action, Attack)
        assert action.target_is_hero

    def test_completes_without_crash(self):
        card_db = {f"c_{i}": {"card_id":f"c_{i}","card_type":"MINION",
            "mana_cost":(i%7)+1,"attack":(i%5)+1,"health":(i%5)+2,
            "mechanics":[],"name":f"C{i}"} for i in range(30)}
        state = GameState(
            PlayerState(hero=HeroState("MAGE"), mana=5, max_mana=5,
                        hand=["c_0","c_1","c_2"], deck=[f"c_{i}" for i in range(10)]),
            PlayerState(hero=HeroState("WARRIOR"),
                        board=[MinionState("e","E",3,4,4,3)]),
        )
        engine = GameEngine(card_db)
        ai = MCTSAI(iterations=30)
        action = ai.choose_action(state, engine)
        assert action is not None
```

- [ ] **Step 2: Run tests → FAIL**
- [ ] **Step 3: Implement MCTSAI**

```python
class MCTSAI(BaseAI):
    """Level 3: Monte Carlo Tree Search AI for high-quality play decisions."""

    def __init__(self, iterations: int = 100, rollout_depth: int = 5):
        self.iterations = iterations
        self.rollout_depth = rollout_depth
        self._rollout_ai = RuleBasedAI()

    def choose_action(self, state: GameState, engine: GameEngine):
        from src.simulator.evaluator import evaluate_state
        from src.simulator.match import _execute_action

        actions = engine.get_legal_actions(state)
        non_end = [a for a in actions if not isinstance(a, EndTurn)]
        if not non_end:
            return EndTurn()

        player_idx = state.current_player_idx
        scores: dict[int, list[float]] = {i: [] for i in range(len(non_end))}

        for _ in range(self.iterations):
            action_idx = random.randint(0, len(non_end) - 1)
            action = non_end[action_idx]
            try:
                sim_state = copy.deepcopy(state)
                sim_engine = GameEngine(card_db=engine.card_db)
                _execute_action(sim_engine, sim_state, action, engine.card_db)
                sim_engine.remove_dead_minions(sim_state)

                # Rollout: play out a few more actions with RuleBasedAI
                for _ in range(self.rollout_depth):
                    if sim_state.game_over:
                        break
                    rollout_action = self._rollout_ai.choose_action(sim_state, sim_engine)
                    if isinstance(rollout_action, EndTurn):
                        break
                    _execute_action(sim_engine, sim_state, rollout_action, engine.card_db)
                    sim_engine.remove_dead_minions(sim_state)

                score = evaluate_state(sim_state, player_idx)
                scores[action_idx].append(score)
            except Exception:
                scores[action_idx].append(-500)

        # Pick action with highest average score
        best_idx = 0
        best_avg = -9999
        for idx, s_list in scores.items():
            if s_list:
                avg = sum(s_list) / len(s_list)
                if avg > best_avg:
                    best_avg = avg
                    best_idx = idx
        return non_end[best_idx]
```

- [ ] **Step 4: Run tests → PASS**
- [ ] **Step 5: Commit**

---

### Task 5: Update match.py to Support AI Selection

**Files:**
- Modify: `src/simulator/match.py`
- Test: `tests/test_ai.py`

Allow `run_match()` to accept an AI class/instance parameter.

- [ ] **Step 1: Write test**

```python
class TestMatchWithAI:
    def test_match_with_rule_based(self):
        from src.simulator.match import run_match
        from src.simulator.ai import RuleBasedAI
        card_db = {f"c_{i}": {"card_id":f"c_{i}","card_type":"MINION",
            "mana_cost":(i%7)+1,"attack":(i%5)+1,"health":(i%5)+2,
            "mechanics":[],"name":f"C{i}"} for i in range(30)}
        deck = [f"c_{i}" for i in range(15)] * 2
        r = run_match(list(deck), list(deck), "MAGE", "WARRIOR", card_db,
                      ai_class=RuleBasedAI)
        assert r.winner in ("A", "B", None)

    def test_match_with_score_based(self):
        from src.simulator.match import run_match
        from src.simulator.ai import ScoreBasedAI
        card_db = {f"c_{i}": {"card_id":f"c_{i}","card_type":"MINION",
            "mana_cost":(i%7)+1,"attack":(i%5)+1,"health":(i%5)+2,
            "mechanics":[],"name":f"C{i}"} for i in range(30)}
        deck = [f"c_{i}" for i in range(15)] * 2
        r = run_match(list(deck), list(deck), "MAGE", "WARRIOR", card_db,
                      ai_class=ScoreBasedAI)
        assert r.winner in ("A", "B", None)
```

- [ ] **Step 2: Run → FAIL**
- [ ] **Step 3: Update `run_match` signature**

```python
def run_match(deck_a, deck_b, hero_a, hero_b, card_db,
              max_turns=45, ai_class=None) -> MatchResult:
    engine = GameEngine(card_db=card_db)
    if ai_class is None:
        from src.simulator.ai import RuleBasedAI
        ai_class = RuleBasedAI
    ai = ai_class()
    # ... rest unchanged
```

- [ ] **Step 4: Run → PASS**
- [ ] **Step 5: Commit**

---

### Task 6: Tournament Runner

**Files:**
- Create: `src/simulator/tournament.py`
- Test: `tests/test_tournament.py`

Round-robin tournament: every deck plays every other deck N times. Outputs matchup matrix, overall win rates, and rankings.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_tournament.py
import pytest
from src.simulator.tournament import Tournament, TournamentResult

@pytest.fixture
def sample_card_db():
    return {f"c_{i}": {"card_id":f"c_{i}","card_type":"MINION",
        "mana_cost":(i%7)+1,"attack":(i%5)+1,"health":(i%5)+2,
        "mechanics":[],"name":f"C{i}"} for i in range(30)}

@pytest.fixture
def sample_decks():
    return {
        "Aggro": {"hero": "HUNTER", "cards": [f"c_{i}" for i in range(15)] * 2},
        "Control": {"hero": "WARRIOR", "cards": [f"c_{i}" for i in range(15)] * 2},
        "Midrange": {"hero": "MAGE", "cards": [f"c_{i}" for i in range(15)] * 2},
    }

class TestTournament:
    def test_round_robin_runs(self, sample_card_db, sample_decks):
        t = Tournament(sample_decks, sample_card_db, matches_per_pair=5)
        result = t.run()
        assert isinstance(result, TournamentResult)
        assert len(result.rankings) == 3

    def test_matchup_matrix(self, sample_card_db, sample_decks):
        t = Tournament(sample_decks, sample_card_db, matches_per_pair=5)
        result = t.run()
        # Should have matchup data for each pair
        assert len(result.matchups) > 0
        for mu in result.matchups:
            assert "deck_a" in mu
            assert "deck_b" in mu
            assert "a_wins" in mu
            assert "b_wins" in mu
            assert "winrate_a" in mu

    def test_rankings_sorted(self, sample_card_db, sample_decks):
        t = Tournament(sample_decks, sample_card_db, matches_per_pair=5)
        result = t.run()
        winrates = [r["overall_winrate"] for r in result.rankings]
        assert winrates == sorted(winrates, reverse=True)

    def test_summary_text(self, sample_card_db, sample_decks):
        t = Tournament(sample_decks, sample_card_db, matches_per_pair=5)
        result = t.run()
        text = result.summary()
        assert "Aggro" in text
        assert "Control" in text
```

- [ ] **Step 2: Run → FAIL**
- [ ] **Step 3: Implement Tournament**

```python
# src/simulator/tournament.py
"""Round-robin tournament simulator with statistical output."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from src.simulator.match import run_match

logger = logging.getLogger(__name__)


@dataclass
class MatchupResult:
    deck_a: str
    deck_b: str
    a_wins: int = 0
    b_wins: int = 0
    draws: int = 0

    @property
    def total(self) -> int:
        return self.a_wins + self.b_wins + self.draws

    @property
    def winrate_a(self) -> float:
        return round(self.a_wins / self.total * 100, 1) if self.total else 0

    @property
    def winrate_b(self) -> float:
        return round(self.b_wins / self.total * 100, 1) if self.total else 0


@dataclass
class TournamentResult:
    matchups: list[dict]
    rankings: list[dict]
    matrix: dict[str, dict[str, float]]

    def summary(self) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("TOURNAMENT RESULTS")
        lines.append("=" * 60)
        lines.append("")

        # Rankings
        lines.append("## Rankings")
        lines.append(f"{'Rank':<6}{'Deck':<20}{'Win%':<10}{'W':<6}{'L':<6}{'D':<6}")
        lines.append("-" * 54)
        for i, r in enumerate(self.rankings, 1):
            lines.append(
                f"{i:<6}{r['deck']:<20}{r['overall_winrate']:>5.1f}%"
                f"    {r['wins']:<6}{r['losses']:<6}{r['draws']:<6}"
            )

        # Matchup Matrix
        lines.append("")
        lines.append("## Matchup Matrix (row win% vs column)")
        deck_names = [r["deck"] for r in self.rankings]
        header = f"{'':>15}" + "".join(f"{d:>12}" for d in deck_names)
        lines.append(header)
        lines.append("-" * len(header))
        for d in deck_names:
            row = f"{d:>15}"
            for opp in deck_names:
                if d == opp:
                    row += f"{'---':>12}"
                else:
                    wr = self.matrix.get(d, {}).get(opp, 0)
                    row += f"{wr:>11.1f}%"
            lines.append(row)

        # Per-matchup detail
        lines.append("")
        lines.append("## Matchup Details")
        for mu in self.matchups:
            lines.append(
                f"  {mu['deck_a']} vs {mu['deck_b']}: "
                f"{mu['a_wins']}W-{mu['b_wins']}W-{mu['draws']}D "
                f"({mu['winrate_a']:.1f}% / {mu['winrate_b']:.1f}%)"
            )

        return "\n".join(lines)


class Tournament:
    def __init__(self, decks: dict[str, dict], card_db: dict,
                 matches_per_pair: int = 50, ai_class=None, max_turns: int = 45):
        self.decks = decks  # {name: {"hero": str, "cards": list[str]}}
        self.card_db = card_db
        self.matches_per_pair = matches_per_pair
        self.ai_class = ai_class
        self.max_turns = max_turns

    def run(self) -> TournamentResult:
        deck_names = list(self.decks.keys())
        matchup_results: list[MatchupResult] = []
        # Track per-deck totals
        stats: dict[str, dict] = {
            name: {"wins": 0, "losses": 0, "draws": 0} for name in deck_names
        }

        for i, name_a in enumerate(deck_names):
            for name_b in deck_names[i + 1:]:
                deck_a = self.decks[name_a]
                deck_b = self.decks[name_b]
                mu = MatchupResult(deck_a=name_a, deck_b=name_b)

                for _ in range(self.matches_per_pair):
                    result = run_match(
                        deck_a=list(deck_a["cards"]),
                        deck_b=list(deck_b["cards"]),
                        hero_a=deck_a["hero"],
                        hero_b=deck_b["hero"],
                        card_db=self.card_db,
                        max_turns=self.max_turns,
                        ai_class=self.ai_class,
                    )
                    if result.winner == "A":
                        mu.a_wins += 1
                    elif result.winner == "B":
                        mu.b_wins += 1
                    else:
                        mu.draws += 1

                matchup_results.append(mu)
                stats[name_a]["wins"] += mu.a_wins
                stats[name_a]["losses"] += mu.b_wins
                stats[name_a]["draws"] += mu.draws
                stats[name_b]["wins"] += mu.b_wins
                stats[name_b]["losses"] += mu.a_wins
                stats[name_b]["draws"] += mu.draws

                logger.info("%s vs %s: %dW-%dW-%dD",
                            name_a, name_b, mu.a_wins, mu.b_wins, mu.draws)

        # Build matchup matrix
        matrix: dict[str, dict[str, float]] = {}
        for mu in matchup_results:
            matrix.setdefault(mu.deck_a, {})[mu.deck_b] = mu.winrate_a
            matrix.setdefault(mu.deck_b, {})[mu.deck_a] = mu.winrate_b

        # Build rankings
        rankings = []
        for name in deck_names:
            s = stats[name]
            total = s["wins"] + s["losses"] + s["draws"]
            wr = round(s["wins"] / total * 100, 1) if total else 0
            rankings.append({
                "deck": name, "wins": s["wins"], "losses": s["losses"],
                "draws": s["draws"], "total_games": total,
                "overall_winrate": wr,
            })
        rankings.sort(key=lambda x: x["overall_winrate"], reverse=True)

        matchups_dicts = [
            {"deck_a": m.deck_a, "deck_b": m.deck_b,
             "a_wins": m.a_wins, "b_wins": m.b_wins, "draws": m.draws,
             "winrate_a": m.winrate_a, "winrate_b": m.winrate_b}
            for m in matchup_results
        ]

        return TournamentResult(
            matchups=matchups_dicts, rankings=rankings, matrix=matrix,
        )
```

- [ ] **Step 4: Run tests → PASS**
- [ ] **Step 5: Commit**

---

### Task 7: Tournament API + Web Page

**Files:**
- Modify: `src/web/routes/api.py`
- Modify: `src/web/routes/pages.py`
- Create: `src/web/templates/tournament.html`
- Modify: `src/web/templates/base.html` (add nav link)

- [ ] **Step 1: Add tournament API endpoint**

```python
# In api.py
@router.post("/tournament/run")
def run_tournament(
    deck_ids: str,  # comma-separated deck IDs
    matches_per_pair: int = 20,
    ai_level: str = "rule",  # "rule", "score", "mcts"
    db: Session = Depends(get_db),
):
    from src.simulator.tournament import Tournament
    from src.simulator.ai import RuleBasedAI, ScoreBasedAI, MCTSAI

    ai_map = {"rule": RuleBasedAI, "score": ScoreBasedAI, "mcts": MCTSAI}
    ai_class = ai_map.get(ai_level, RuleBasedAI)

    ids = [int(x.strip()) for x in deck_ids.split(",")]
    decks_data = {}
    # ... load decks from DB, build card_db ...

    t = Tournament(decks_data, combined_card_db,
                   matches_per_pair=min(matches_per_pair, 100),
                   ai_class=ai_class)
    result = t.run()
    return {"success": True, "rankings": result.rankings,
            "matchups": result.matchups, "matrix": result.matrix}
```

- [ ] **Step 2: Add tournament page template**

Tournament page shows:
- Deck selector (checkboxes for 2-8 decks)
- AI level selector (Rule / Score / MCTS)
- Matches per pair input
- Run button
- Results: rankings table + matchup matrix heatmap

- [ ] **Step 3: Add nav link in base.html**
- [ ] **Step 4: Test end-to-end**
- [ ] **Step 5: Commit**

---

### Task 8: CLI Tournament Command

**Files:**
- Modify: `main.py`

Add `python main.py tournament` command for running tournaments from CLI with text output.

- [ ] **Step 1: Add tournament subcommand**

```python
tournament_parser = subparsers.add_parser("tournament", help="Run round-robin tournament")
tournament_parser.add_argument("--matches", type=int, default=50)
tournament_parser.add_argument("--ai", choices=["rule","score","mcts"], default="rule")
```

- [ ] **Step 2: Implement tournament CLI**
- [ ] **Step 3: Test with sample decks**
- [ ] **Step 4: Commit**

---

### Task 9: Integration Test — Full 5-Deck Tournament

**Files:**
- Test: `tests/test_tournament.py`

- [ ] **Step 1: Write 5-deck tournament integration test**

```python
def test_five_deck_tournament(sample_card_db):
    """Simulate a real 5-deck tournament scenario."""
    # 5 decks with different card distributions to simulate archetypes
    decks = {}
    classes = ["HUNTER", "WARRIOR", "MAGE", "PRIEST", "ROGUE"]
    for i, cls in enumerate(classes):
        # Shift card pool slightly per deck for variety
        cards = [f"c_{(j + i*3) % 30}" for j in range(15)] * 2
        decks[f"{cls.title()} Deck"] = {"hero": cls, "cards": cards}

    t = Tournament(decks, sample_card_db, matches_per_pair=10)
    result = t.run()

    assert len(result.rankings) == 5
    assert len(result.matchups) == 10  # C(5,2) = 10 pairs
    print(result.summary())
```

- [ ] **Step 2: Run → PASS + review summary output**
- [ ] **Step 3: Commit + push**
