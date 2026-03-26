from __future__ import annotations
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TierEntry:
    deck_name: str
    hero_class: str
    archetype: str
    tier: str        # "S", "A", "B", "C", "D"
    winrate: float
    card_ids: list[str] = field(default_factory=list)


@dataclass
class MetaReport:
    tier_list: list[TierEntry]
    total_decks: int = 0
    total_matches: int = 0

    def summary(self) -> str:
        lines = ["=== META TIER LIST ===", ""]
        # Sort: S first (lowest ord), then by winrate descending
        tier_order = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4}
        sorted_entries = sorted(
            self.tier_list,
            key=lambda e: (tier_order.get(e.tier, 5), -e.winrate),
        )

        current_tier = ""
        for entry in sorted_entries:
            if entry.tier != current_tier:
                current_tier = entry.tier
                lines.append(f"--- Tier {current_tier} ---")
            lines.append(f"  {entry.winrate:5.1f}% | {entry.deck_name} ({entry.hero_class})")

        lines.append(f"\nTotal: {self.total_decks} decks, {self.total_matches} matches")
        return "\n".join(lines)


class MetaDeckBuilder:
    """Orchestrates the full meta deck building pipeline:
    Phase 1: Generate seed decks from archetype recipes
    Phase 2: Optimize via evolutionary simulation
    Phase 3: Tournament to produce tier list
    """

    def __init__(
        self,
        db_session,
        classes: list[str] | None = None,
        archetypes: list[str] | None = None,
        matches_per_pair: int = 20,
        optimization_generations: int = 3,
        optimization_matches: int = 5,
        mutation_count: int = 2,
        max_decks_per_class: int = 3,
        ai_class=None,
    ):
        self.db = db_session
        self.classes = classes
        self.archetypes = archetypes
        self.matches_per_pair = matches_per_pair
        self.opt_generations = optimization_generations
        self.opt_matches = optimization_matches
        self.mutation_count = mutation_count
        self.max_decks_per_class = max_decks_per_class
        self.ai_class = ai_class
        self.card_db = {}
        self._optimized_decks: list[dict] = []
        self._matchup_matrix: dict = {}

    def run(self) -> MetaReport:
        """Execute the full pipeline."""
        logger.info("Phase 0: Building card database...")
        self.card_db = self._build_card_db()
        logger.info(f"  {len(self.card_db)} cards loaded")

        logger.info("Phase 1: Generating seed decks...")
        seeds = self._phase1_generate()
        logger.info(f"  {len(seeds)} seed decks generated")

        logger.info("Phase 2: Optimizing decks...")
        optimized = self._phase2_optimize(seeds)
        logger.info(f"  {len(optimized)} decks after optimization")

        # Cache optimized decks for Phase 4 use
        self._optimized_decks = optimized

        logger.info("Phase 3: Running meta tournament...")
        report = self._phase3_tournament(optimized)
        logger.info(f"  Done! {report.total_decks} decks ranked")

        return report

    def _build_card_db(self) -> dict:
        """Build card_db from database for all standard collectible cards."""
        from src.db.tables import Card
        import json

        cards = self.db.query(Card).filter(
            Card.is_standard == True,
            Card.collectible == True,
        ).all()

        card_db = {}
        for c in cards:
            mechs = c.mechanics or []
            if isinstance(mechs, str):
                mechs = [m.strip() for m in mechs.split(",") if m.strip()]

            # Extract race from json_data
            race = ""
            races = []
            jd = c.json_data
            if jd:
                if isinstance(jd, str):
                    try:
                        jd = json.loads(jd)
                    except Exception:
                        jd = {}
                if isinstance(jd, dict):
                    race = jd.get("race", "") or ""
                    races = jd.get("races", []) or []

            card_db[c.card_id] = {
                "card_id": c.card_id,
                "card_type": c.card_type or "MINION",
                "name": c.name or "",
                "mana_cost": c.mana_cost or 0,
                "attack": c.attack or 0,
                "health": c.health or 0,
                "durability": c.durability or 1,
                "mechanics": mechs,
                "text": c.text or "",
                "rarity": c.rarity or "",
                "hero_class": c.hero_class or "NEUTRAL",
                "race": race,
                "races": races,
                "collectible": True,
            }

        return card_db

    def _phase1_generate(self) -> list[dict]:
        """Generate seed decks from recipes."""
        from src.deckbuilder.recipes import build_recipes
        from src.deckbuilder.synergy import build_deck_from_recipe

        recipes = build_recipes(classes=self.classes, archetypes=self.archetypes)
        seeds = []

        # Track per-class count
        class_count = {}
        for recipe in recipes:
            cls = recipe.hero_class
            if class_count.get(cls, 0) >= self.max_decks_per_class:
                continue

            try:
                deck = build_deck_from_recipe(recipe, self.card_db)
                if len(deck["cards"]) >= 30:
                    seeds.append(deck)
                    class_count[cls] = class_count.get(cls, 0) + 1
            except Exception as e:
                logger.warning(f"Failed to build {recipe.name}: {e}")

        return seeds

    def _phase2_optimize(self, seeds: list[dict]) -> list[dict]:
        """Optimize decks via evolutionary simulation."""
        from src.deckbuilder.optimizer import DeckOptimizer

        if len(seeds) < 2:
            return seeds

        optimizer = DeckOptimizer(
            card_db=self.card_db,
            matches_per_eval=self.opt_matches,
            generations=self.opt_generations,
            mutation_count=self.mutation_count,
        )

        return optimizer.optimize(seeds)

    def _phase3_tournament(self, decks: list[dict]) -> MetaReport:
        """Run round-robin tournament and produce tier list."""
        from src.simulator.tournament import Tournament

        if len(decks) < 2:
            return MetaReport(tier_list=[], total_decks=len(decks))

        # Convert to Tournament format
        tourney_decks = {}
        for d in decks:
            name = d["name"]
            # Ensure unique names
            if name in tourney_decks:
                name = f"{name} ({d.get('archetype', '')})"
            tourney_decks[name] = {
                "hero": d["hero"],
                "cards": d["cards"],
            }

        ai_class = self.ai_class
        if ai_class is None:
            from src.simulator.ai import RuleBasedAI
            ai_class = RuleBasedAI

        tourney = Tournament(
            tourney_decks, self.card_db,
            matches_per_pair=self.matches_per_pair,
            ai_class=ai_class,
        )
        result = tourney.run()

        # Cache matchup matrix for Phase 4 use
        self._matchup_matrix = result.matrix

        # Build tier list from tournament rankings
        # result is a TournamentResult dataclass with .rankings attribute
        tier_list = []
        for ranking in result.rankings:
            name = ranking["deck"]
            wr = ranking.get("overall_winrate", 50.0)

            # Find the original deck data
            deck_data = None
            for d in decks:
                if d["name"] == name or f"{d['name']} ({d.get('archetype', '')})" == name:
                    deck_data = d
                    break

            # Assign tier
            if wr >= 60:
                tier = "S"
            elif wr >= 52:
                tier = "A"
            elif wr >= 48:
                tier = "B"
            elif wr >= 40:
                tier = "C"
            else:
                tier = "D"

            tier_list.append(TierEntry(
                deck_name=name,
                hero_class=deck_data["hero"] if deck_data else "",
                archetype=deck_data.get("archetype", "") if deck_data else "",
                tier=tier,
                winrate=wr,
                card_ids=deck_data["cards"] if deck_data else [],
            ))

        # Sort by tier then winrate
        tier_order = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4}
        tier_list.sort(key=lambda e: (tier_order.get(e.tier, 5), -e.winrate))

        return MetaReport(
            tier_list=tier_list,
            total_decks=len(decks),
            total_matches=self.matches_per_pair * len(decks) * (len(decks) - 1) // 2,
        )

    def find_ladder_king(self, meta_weights: dict | None = None) -> "LadderResult":
        """Phase 4A: Find the single best deck for climbing ranked ladder.

        Must call run() first to build the deck pool and matchup matrix.
        Returns: LadderResult with best deck and matchup details.
        """
        from src.deckbuilder.ladder import LadderOptimizer

        optimizer = LadderOptimizer(
            card_db=self.card_db,
            meta_field=self._optimized_decks,
            meta_weights=meta_weights,
            generations=3,
            matches_per_eval=self.opt_matches,
        )
        return optimizer.find_best(self._optimized_decks, self._matchup_matrix)

    def find_championship_lineup(self, opponent_lineups=None) -> "LineupResult":
        """Phase 4B: Find the best 4-deck Conquest lineup for World Championship.

        Must call run() first to build the deck pool and matchup matrix.
        Returns: LineupResult with 4 decks, conquest winrate, and ban recommendations.
        """
        from src.deckbuilder.lineup import LineupOptimizer

        optimizer = LineupOptimizer(
            deck_pool=self._optimized_decks,
            matchup_matrix=self._matchup_matrix,
            card_db=self.card_db,
        )
        return optimizer.find_best_lineup(opponent_lineups)

    def full_analysis(self, meta_weights=None) -> dict:
        """Run everything: meta tier list + ladder king + championship lineup."""
        report = self.run()
        ladder = self.find_ladder_king(meta_weights)
        lineup = self.find_championship_lineup()
        return {
            "meta_report": report,
            "ladder_king": ladder,
            "championship_lineup": lineup,
        }
