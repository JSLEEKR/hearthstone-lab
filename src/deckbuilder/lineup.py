"""Championship Lineup optimizer — find the best 4-deck Conquest lineup."""
from __future__ import annotations
import random
from itertools import combinations
from dataclasses import dataclass, field


@dataclass
class LineupResult:
    decks: list[dict]  # 4 deck dicts
    conquest_winrate: float  # estimated series winrate
    ban_resilience: float  # worst-case ban score
    recommended_bans: dict  # {opponent_lineup_name: deck_to_ban}


class LineupOptimizer:
    """Find the best 4-deck Conquest lineup from a pool of optimized decks.

    World Championship rules:
    - 4 decks, each different class
    - Opponent bans 1, we ban 1
    - Must win with each remaining deck (Conquest)

    Optimization strategy:
    1. Group decks by class
    2. Enumerate all valid 4-class combinations
    3. For each combo, evaluate conquest series winrate
    4. Score by worst-case ban resilience (min across all opponent bans)
    5. Return the most robust lineup
    """

    def __init__(self, deck_pool: list[dict], matchup_matrix: dict,
                 card_db: dict, num_lineup_decks: int = 4,
                 conquest_sims: int = 100):
        self.deck_pool = deck_pool
        self.matrix = matchup_matrix
        self.card_db = card_db
        self.num_decks = num_lineup_decks
        self.conquest_sims = conquest_sims

    def find_best_lineup(self, opponent_lineups: list[list[dict]] | None = None) -> LineupResult:
        """Find the best lineup from the deck pool.

        Args:
            opponent_lineups: list of opponent lineups (each is list of 4 dicts).
                If None, uses the deck pool as the opponent field.
        """
        from src.simulator.conquest import (
            evaluate_lineup, heuristic_ban, simulate_conquest_series,
            lineup_ban_resilience,
        )

        # Group decks by class
        by_class: dict[str, list[dict]] = {}
        for d in self.deck_pool:
            cls = d.get("hero", "NEUTRAL")
            by_class.setdefault(cls, []).append(d)

        classes = [cls for cls, decks in by_class.items() if decks]

        if len(classes) < self.num_decks:
            # Not enough classes — use what we have
            lineup = []
            for cls in classes:
                lineup.append(by_class[cls][0])
            return LineupResult(
                decks=lineup,
                conquest_winrate=0.5,
                ban_resilience=0.5,
                recommended_bans={},
            )

        # Generate opponent lineups if not provided
        if not opponent_lineups:
            # Create hypothetical opponent lineups from our own pool
            opponent_lineups = self._generate_opponent_lineups(by_class, classes)

        # Enumerate all valid 4-class combinations
        best_lineup = None
        best_score = -1
        best_wr = 0
        best_resilience = 0
        best_bans = {}

        for class_combo in combinations(classes, self.num_decks):
            # For each class, pick the best deck (highest fitness or first available)
            lineup = []
            for cls in class_combo:
                # Pick best deck from this class (sorted by fitness if available)
                candidates = sorted(by_class[cls],
                                     key=lambda d: d.get("fitness", 0), reverse=True)
                lineup.append(candidates[0])

            # Evaluate this lineup
            wr = evaluate_lineup(lineup, opponent_lineups, self.matrix,
                                  num_sims=self.conquest_sims)
            resilience = lineup_ban_resilience(lineup, self.deck_pool, self.matrix,
                                                num_sims=self.conquest_sims // 2)

            # Combined score: 70% winrate + 30% resilience
            score = wr * 0.7 + resilience * 0.3

            if score > best_score:
                best_score = score
                best_lineup = lineup
                best_wr = wr
                best_resilience = resilience

                # Compute recommended bans
                best_bans = {}
                for opp_lineup in opponent_lineups:
                    opp_key = "_".join(d.get("name", "?") for d in opp_lineup[:2])
                    ban = heuristic_ban(lineup, opp_lineup, self.matrix)
                    best_bans[opp_key] = ban

        if best_lineup is None:
            best_lineup = [by_class[cls][0] for cls in classes[:self.num_decks]]

        return LineupResult(
            decks=best_lineup,
            conquest_winrate=best_wr,
            ban_resilience=best_resilience,
            recommended_bans=best_bans,
        )

    def _generate_opponent_lineups(self, by_class: dict, classes: list) -> list[list[dict]]:
        """Generate hypothetical opponent lineups from the deck pool."""
        lineups = []

        # Generate up to 5 random lineups
        for _ in range(min(5, len(list(combinations(classes, self.num_decks))))):
            if len(classes) >= self.num_decks:
                chosen = random.sample(classes, self.num_decks)
            else:
                chosen = classes[:]

            lineup = []
            for cls in chosen:
                decks = by_class.get(cls, [])
                if decks:
                    lineup.append(random.choice(decks))

            if len(lineup) >= self.num_decks:
                lineups.append(lineup)

        # If we couldn't generate any, use single-deck "lineups"
        if not lineups:
            lineups = [[d] for d in self.deck_pool[:5]]

        return lineups
