"""Ladder King optimizer — find the single best deck for climbing ranked."""
from __future__ import annotations
import random
import copy
from dataclasses import dataclass
from src.deckbuilder.optimizer import DeckOptimizer, DeckGenome


@dataclass
class LadderResult:
    best_deck: dict  # {name, hero, cards, archetype, winrate}
    matchup_details: dict  # {opponent_name: winrate}
    meta_score: float  # weighted winrate


class LadderOptimizer:
    """Find the best ladder deck by optimizing weighted winrate across the meta field.

    Unlike standard DeckOptimizer which just plays random opponents,
    LadderOptimizer:
    1. Plays against ALL meta decks (weighted by frequency)
    2. Penalizes decks with any matchup below 30%
    3. Uses targeted mutations to fix worst matchups
    """

    def __init__(self, card_db: dict, meta_field: list[dict],
                 meta_weights: dict | None = None,
                 generations: int = 5, matches_per_eval: int = 10,
                 bad_matchup_penalty: float = 5.0):
        self.card_db = card_db
        self.meta_field = meta_field  # list of deck dicts
        self.meta_weights = meta_weights or {}
        self.generations = generations
        self.matches_per_eval = matches_per_eval
        self.bad_matchup_penalty = bad_matchup_penalty
        self._optimizer = DeckOptimizer(card_db, matches_per_eval=matches_per_eval,
                                         generations=1, mutation_count=1)

    def find_best(self, candidates: list[dict], matrix: dict) -> LadderResult:
        """Find the best ladder deck from candidates using the matchup matrix.

        Args:
            candidates: list of deck dicts {name, hero, cards, archetype}
            matrix: matrix[deck_a][deck_b] = winrate (0-100)
        """
        if not candidates:
            return LadderResult(best_deck={}, matchup_details={}, meta_score=0)

        # Score each candidate
        scored = []
        for deck in candidates:
            score, details = self._score_deck(deck["name"], matrix)
            scored.append((score, deck, details))

        scored.sort(key=lambda x: -x[0])

        # Take top candidates and try to optimize them further
        top_n = min(5, len(scored))
        best_score = scored[0][0]
        best_deck = scored[0][1]
        best_details = scored[0][2]

        # Evolutionary refinement on top candidates
        from src.simulator.match import run_match

        for score, deck, details in scored[:top_n]:
            genome = DeckGenome(
                card_ids=list(deck["cards"]),
                hero_class=deck["hero"],
                archetype=deck.get("archetype", ""),
                name=deck["name"],
            )

            # Try mutations, keep if they improve weighted score
            for gen in range(self.generations):
                mutant = self._optimizer._mutate(genome)
                mutant_deck = {
                    "name": f"{deck['name']}_mut",
                    "hero": mutant.hero_class,
                    "cards": mutant.card_ids,
                    "archetype": mutant.archetype,
                }

                # Evaluate mutant against meta field via actual simulation
                mutant_wr = self._evaluate_vs_field(mutant_deck)
                current_wr = score

                if mutant_wr > current_wr:
                    genome = mutant
                    score = mutant_wr
                    deck = mutant_deck

            if score > best_score:
                best_score = score
                best_deck = deck
                best_details = details

        best_deck["winrate"] = best_score
        return LadderResult(
            best_deck=best_deck,
            matchup_details=best_details,
            meta_score=best_score,
        )

    def _score_deck(self, deck_name: str, matrix: dict) -> tuple[float, dict]:
        """Score a deck using weighted winrate with bad matchup penalty."""
        details = {}
        total_weight = 0
        weighted_wr = 0
        penalty = 0

        # Default weight: uniform
        default_weight = 1.0 / max(len(self.meta_field), 1)

        for opp in self.meta_field:
            opp_name = opp["name"]
            if opp_name == deck_name:
                continue
            weight = self.meta_weights.get(opp_name, default_weight)
            wr = matrix.get(deck_name, {}).get(opp_name, 50.0)
            details[opp_name] = wr
            weighted_wr += wr * weight
            total_weight += weight

            # Penalty for bad matchups
            if wr < 30:
                penalty += (30 - wr) * self.bad_matchup_penalty * weight

        score = (weighted_wr / max(total_weight, 0.01)) - penalty
        return score, details

    def _evaluate_vs_field(self, deck: dict) -> float:
        """Evaluate a deck by simulating against the meta field."""
        from src.simulator.match import run_match

        wins = 0
        games = 0
        for opp in self.meta_field:
            if opp["name"] == deck["name"]:
                continue
            for _ in range(self.matches_per_eval):
                try:
                    r = run_match(
                        list(deck["cards"]), list(opp["cards"]),
                        deck["hero"], opp["hero"],
                        self.card_db, max_turns=60
                    )
                    games += 1
                    if r.winner == "A":
                        wins += 1
                except Exception:
                    pass

        return (wins / max(games, 1)) * 100
