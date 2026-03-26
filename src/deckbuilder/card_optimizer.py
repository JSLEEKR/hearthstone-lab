"""Statistical card-level deck optimization.

Process:
1. Run baseline games with card tracking
2. Identify underperforming cards
3. Find replacement candidates
4. Validate replacements via simulation
5. Accept statistically significant improvements
"""
from __future__ import annotations
import math
import random
from dataclasses import dataclass, field


@dataclass
class ReplacementResult:
    card_removed: str
    card_removed_name: str
    card_added: str
    card_added_name: str
    original_winrate: float
    new_winrate: float
    delta: float
    z_score: float
    significant: bool
    games_played: int


@dataclass
class OptimizationReport:
    deck_name: str
    original_winrate: float
    optimized_winrate: float
    card_changes: list[ReplacementResult] = field(default_factory=list)
    underperformers: list[dict] = field(default_factory=list)  # card stats summaries
    optimized_deck: dict = field(default_factory=dict)

    def summary(self) -> str:
        lines = [f"=== {self.deck_name} Optimization ==="]
        lines.append(f"Winrate: {self.original_winrate:.1f}% -> {self.optimized_winrate:.1f}% ({self.optimized_winrate - self.original_winrate:+.1f}%)")
        if self.underperformers:
            lines.append(f"Underperformers found: {len(self.underperformers)}")
            for up in self.underperformers[:5]:
                lines.append(f"  {up['name']} (score={up['score']:.1f}, play_rate={up['play_rate']:.0%}, drawn_wr_delta={up['drawn_wr_delta']:+.1f}%)")
        if self.card_changes:
            lines.append(f"Changes made: {len(self.card_changes)}")
            for ch in self.card_changes:
                lines.append(f"  OUT: {ch.card_removed_name} -> IN: {ch.card_added_name} ({ch.delta:+.1f}%, z={ch.z_score:.2f})")
        else:
            lines.append("No statistically significant improvements found.")
        return "\n".join(lines)


class CardDeckOptimizer:
    """Optimize a deck by identifying and replacing underperforming cards."""

    def __init__(self, card_db: dict, opponent_decks: list[dict],
                 games_per_eval: int = 50, max_replacements: int = 5,
                 min_improvement: float = 1.0, confidence: float = 1.28):
        self.card_db = card_db
        self.opponents = opponent_decks
        self.games_per_eval = games_per_eval
        self.max_replacements = max_replacements
        self.min_improvement = min_improvement  # minimum winrate delta to accept
        self.confidence = confidence  # z-score threshold (1.28 = 90% one-tailed)

    def optimize_deck(self, deck: dict) -> OptimizationReport:
        """Full optimization pipeline for one deck."""
        from src.simulator.match import run_match
        from src.simulator.card_stats import CardPerformanceRecord, GameCardTracker
        from src.simulator.evaluator import evaluate_state

        deck_name = deck.get("name", "Unknown")
        hero = deck["hero"]
        original_cards = list(deck["cards"])

        # Step 1: Baseline -- run games with card tracking
        records: dict[str, CardPerformanceRecord] = {}
        baseline_wins = 0
        baseline_games = 0

        for opp in self.opponents:
            if opp.get("name") == deck_name:
                continue
            games_vs = max(self.games_per_eval // max(len(self.opponents) - 1, 1), 5)
            for _ in range(games_vs):
                try:
                    result = run_match(
                        list(original_cards), list(opp["cards"]),
                        hero, opp["hero"], self.card_db, max_turns=60
                    )
                    baseline_games += 1
                    won = result.winner == "A"
                    if won:
                        baseline_wins += 1

                    # Simple tracking: record which unique cards were in deck
                    tracker = GameCardTracker(original_cards)
                    # We can't instrument inside run_match without modifying it,
                    # so we use a simplified approach: mark all cards as "drawn"
                    # for stats purposes and use result to determine win correlation
                    unique_cards = set(original_cards)
                    for cid in unique_cards:
                        tracker.drawn.add(cid)
                    tracker.finalize(won, records)
                except Exception:
                    pass

        baseline_wr = baseline_wins / max(baseline_games, 1) * 100

        # Step 2: Identify underperformers
        underperformers = []
        for cid, rec in records.items():
            if rec.games_in_deck < 10:
                continue
            card_data = self.card_db.get(cid, {})
            score = rec.underperformance_score
            underperformers.append({
                "card_id": cid,
                "name": card_data.get("name", cid),
                "score": score,
                "play_rate": rec.play_rate,
                "drawn_wr_delta": rec.drawn_winrate_delta * 100,
                "dead_card_rate": rec.dead_card_rate,
                "board_impact": rec.avg_board_impact,
            })

        underperformers.sort(key=lambda x: -x["score"])

        # Step 3 & 4: Find and validate replacements
        current_cards = list(original_cards)
        changes = []

        for up in underperformers[:self.max_replacements]:
            cid_remove = up["card_id"]
            if cid_remove not in current_cards:
                continue

            candidates = self._find_candidates(cid_remove, current_cards)
            best_replacement = None
            best_delta = 0

            for candidate_id in candidates[:5]:
                result = self._validate_replacement(
                    current_cards, cid_remove, candidate_id, hero
                )
                if result.significant and result.delta > best_delta:
                    best_delta = result.delta
                    best_replacement = result

            if best_replacement:
                # Accept the replacement
                while cid_remove in current_cards:
                    idx = current_cards.index(cid_remove)
                    current_cards[idx] = best_replacement.card_added
                changes.append(best_replacement)

        # Step 5: Final evaluation
        final_wins = 0
        final_games = 0
        for opp in self.opponents:
            if opp.get("name") == deck_name:
                continue
            for _ in range(self.games_per_eval // max(len(self.opponents) - 1, 1)):
                try:
                    result = run_match(
                        list(current_cards), list(opp["cards"]),
                        hero, opp["hero"], self.card_db, max_turns=60
                    )
                    final_games += 1
                    if result.winner == "A":
                        final_wins += 1
                except Exception:
                    pass

        final_wr = final_wins / max(final_games, 1) * 100

        optimized_deck = dict(deck)
        optimized_deck["cards"] = current_cards
        optimized_deck["name"] = deck_name + " (optimized)"

        return OptimizationReport(
            deck_name=deck_name,
            original_winrate=baseline_wr,
            optimized_winrate=final_wr,
            card_changes=changes,
            underperformers=underperformers[:10],
            optimized_deck=optimized_deck,
        )

    def _find_candidates(self, card_to_remove: str, current_deck: list[str]) -> list[str]:
        """Find replacement candidates for a card."""
        removed_card = self.card_db.get(card_to_remove, {})
        removed_cost = removed_card.get("mana_cost", 0) or 0
        removed_class = removed_card.get("hero_class", "NEUTRAL")

        # Determine deck class
        from collections import Counter
        class_counts = Counter()
        for cid in current_deck:
            hc = self.card_db.get(cid, {}).get("hero_class", "NEUTRAL")
            if hc != "NEUTRAL":
                class_counts[hc] += 1
        deck_class = class_counts.most_common(1)[0][0] if class_counts else "NEUTRAL"

        candidates = []
        for cid, card in self.card_db.items():
            # Must be same class or neutral
            hc = card.get("hero_class", "NEUTRAL")
            if hc not in (deck_class, "NEUTRAL"):
                continue
            # Skip hero cards
            if card.get("card_type") == "HERO":
                continue
            # Similar mana cost (+/- 1)
            cost = card.get("mana_cost", 0) or 0
            if abs(cost - removed_cost) > 1:
                continue
            # Not already at max copies in deck
            max_copies = 1 if card.get("rarity") == "LEGENDARY" else 2
            if current_deck.count(cid) >= max_copies:
                continue
            # Not the card being removed
            if cid == card_to_remove:
                continue

            candidates.append(cid)

        # Score candidates by synergy with remaining deck
        from src.deckbuilder.synergy import score_card_for_recipe, detect_synergies
        from src.deckbuilder.recipes import DeckRecipe

        # Create a simple recipe for scoring
        recipe = DeckRecipe(name="opt", hero_class=deck_class, archetype="midrange")
        remaining = [self.card_db.get(c, {}) for c in current_deck if c != card_to_remove]

        scored = []
        for cid in candidates:
            card_data = self.card_db.get(cid, {})
            score = score_card_for_recipe(card_data, recipe, remaining)
            scored.append((score, cid))

        scored.sort(key=lambda x: -x[0])
        return [cid for _, cid in scored]

    def _validate_replacement(self, deck: list[str], remove_id: str,
                               add_id: str, hero: str) -> ReplacementResult:
        """Validate a single card replacement via simulation."""
        from src.simulator.match import run_match

        # Create modified deck
        modified = list(deck)
        while remove_id in modified:
            idx = modified.index(remove_id)
            modified[idx] = add_id

        orig_wins = 0
        mod_wins = 0
        games = 0

        for opp in self.opponents:
            games_vs = max(self.games_per_eval // max(len(self.opponents), 1), 3)
            for _ in range(games_vs):
                try:
                    # Original
                    r1 = run_match(list(deck), list(opp["cards"]),
                                   hero, opp["hero"], self.card_db, max_turns=60)
                    # Modified
                    r2 = run_match(list(modified), list(opp["cards"]),
                                   hero, opp["hero"], self.card_db, max_turns=60)
                    games += 1
                    if r1.winner == "A":
                        orig_wins += 1
                    if r2.winner == "A":
                        mod_wins += 1
                except Exception:
                    pass

        if games == 0:
            return ReplacementResult(
                card_removed=remove_id, card_removed_name=self.card_db.get(remove_id, {}).get("name", remove_id),
                card_added=add_id, card_added_name=self.card_db.get(add_id, {}).get("name", add_id),
                original_winrate=0, new_winrate=0, delta=0, z_score=0,
                significant=False, games_played=0,
            )

        p_orig = orig_wins / games
        p_mod = mod_wins / games
        delta = (p_mod - p_orig) * 100

        # Two-proportion z-test
        p_pooled = (orig_wins + mod_wins) / (2 * games)
        if p_pooled > 0 and p_pooled < 1:
            se = math.sqrt(p_pooled * (1 - p_pooled) * (2 / games))
            z = (p_mod - p_orig) / se if se > 0 else 0
        else:
            z = 0

        significant = delta >= self.min_improvement and z >= self.confidence

        return ReplacementResult(
            card_removed=remove_id,
            card_removed_name=self.card_db.get(remove_id, {}).get("name", remove_id),
            card_added=add_id,
            card_added_name=self.card_db.get(add_id, {}).get("name", add_id),
            original_winrate=p_orig * 100,
            new_winrate=p_mod * 100,
            delta=delta,
            z_score=z,
            significant=significant,
            games_played=games,
        )
