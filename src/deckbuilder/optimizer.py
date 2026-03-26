from __future__ import annotations
import random
import copy
from dataclasses import dataclass, field


@dataclass
class DeckGenome:
    card_ids: list[str]
    hero_class: str
    archetype: str
    name: str = ""
    fitness: float = 0.0
    generation: int = 0


class DeckOptimizer:
    def __init__(self, card_db: dict, matches_per_eval: int = 10,
                 generations: int = 5, mutation_count: int = 2):
        self.card_db = card_db
        self.matches_per_eval = matches_per_eval
        self.generations = generations
        self.mutation_count = mutation_count  # cards to swap per mutation

    def optimize(self, seed_decks: list[dict]) -> list[dict]:
        """Optimize seed decks through evolutionary simulation.

        Args:
            seed_decks: list of {"name", "hero", "cards", "archetype"}
        Returns:
            list of optimized deck dicts in same format
        """
        from src.simulator.match import run_match
        from src.simulator.ai import RuleBasedAI

        if len(seed_decks) < 2:
            return seed_decks

        # Convert to genomes
        population = []
        for d in seed_decks:
            population.append(DeckGenome(
                card_ids=list(d["cards"]),
                hero_class=d["hero"],
                archetype=d.get("archetype", "midrange"),
                name=d["name"],
            ))

        for gen in range(self.generations):
            # Evaluate fitness: each genome plays against random opponents
            for genome in population:
                opponents = [g for g in population if g is not genome]
                if not opponents:
                    continue
                # Play against up to 3 random opponents
                sample = random.sample(opponents, min(3, len(opponents)))
                wins = 0
                games = 0
                for opp in sample:
                    for _ in range(self.matches_per_eval):
                        try:
                            result = run_match(
                                list(genome.card_ids), list(opp.card_ids),
                                genome.hero_class, opp.hero_class,
                                self.card_db, max_turns=60
                            )
                            games += 1
                            if result.winner == "A":
                                wins += 1
                        except Exception:
                            pass
                genome.fitness = wins / max(games, 1)
                genome.generation = gen

            # Sort by fitness
            population.sort(key=lambda g: -g.fitness)

            # Keep top half, mutate bottom half
            half = len(population) // 2
            if half < 1:
                continue

            new_pop = population[:half]  # survivors
            for i in range(half, len(population)):
                # Mutate a copy of a random survivor
                parent = random.choice(new_pop[:half])
                child = self._mutate(parent)
                child.name = parent.name + f" v{gen+1}"
                new_pop.append(child)

            population = new_pop

        # Convert back to dicts
        results = []
        for g in sorted(population, key=lambda x: -x.fitness):
            results.append({
                "name": g.name,
                "hero": g.hero_class,
                "cards": g.card_ids,
                "archetype": g.archetype,
                "fitness": g.fitness,
            })
        return results

    def _mutate(self, genome: DeckGenome) -> DeckGenome:
        """Swap mutation_count cards with random alternatives from card_db."""
        new_ids = list(genome.card_ids)
        hero = genome.hero_class

        # Get available replacements for this class
        replacements = []
        for cid, card in self.card_db.items():
            hc = card.get("hero_class", "NEUTRAL")
            if hc in (hero, "NEUTRAL"):
                if card.get("card_type") != "HERO":
                    replacements.append(cid)

        if not replacements:
            return DeckGenome(card_ids=new_ids, hero_class=hero,
                              archetype=genome.archetype, name=genome.name)

        # Remove random cards and replace
        for _ in range(min(self.mutation_count, len(new_ids))):
            remove_idx = random.randint(0, len(new_ids) - 1)
            new_ids.pop(remove_idx)

            # Add a random replacement (respecting copy limits)
            for attempt in range(20):
                rep = random.choice(replacements)
                max_copies = 1 if self.card_db.get(rep, {}).get("rarity") == "LEGENDARY" else 2
                if new_ids.count(rep) < max_copies:
                    new_ids.append(rep)
                    break
            else:
                # Couldn't find valid replacement, add back something random
                new_ids.append(random.choice(replacements))

        return DeckGenome(
            card_ids=new_ids, hero_class=hero,
            archetype=genome.archetype, name=genome.name
        )
