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
        lines.append("## Rankings")
        lines.append(f"{'Rank':<6}{'Deck':<20}{'Win%':<10}{'W':<6}{'L':<6}{'D':<6}")
        lines.append("-" * 54)
        for i, r in enumerate(self.rankings, 1):
            lines.append(
                f"{i:<6}{r['deck']:<20}{r['overall_winrate']:>5.1f}%"
                f"    {r['wins']:<6}{r['losses']:<6}{r['draws']:<6}"
            )
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
                 matches_per_pair: int = 50, ai_class=None, max_turns: int = 60):
        self.decks = decks
        self.card_db = card_db
        self.matches_per_pair = matches_per_pair
        self.ai_class = ai_class
        self.max_turns = max_turns

    def run(self) -> TournamentResult:
        deck_names = list(self.decks.keys())
        matchup_results: list[MatchupResult] = []
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

        matrix: dict[str, dict[str, float]] = {}
        for mu in matchup_results:
            matrix.setdefault(mu.deck_a, {})[mu.deck_b] = mu.winrate_a
            matrix.setdefault(mu.deck_b, {})[mu.deck_a] = mu.winrate_b

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
