"""Hearthstone Conquest format simulation.

World Championship rules:
- Each player brings 4 decks (different classes)
- Each player bans 1 opponent deck (simultaneous)
- 3 remaining decks per player
- Must win 1 game with EACH deck (checked off on win)
- On loss, can replay any unchecked deck
- First to 3 wins (each with different deck) wins the series
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field


@dataclass
class ConquestResult:
    winner: str  # "A" or "B"
    games_played: int
    a_wins: list[str]  # deck names A won with
    b_wins: list[str]  # deck names B won with
    a_ban: str
    b_ban: str


def simulate_conquest_game(
    wr_a: float,  # winrate of A's deck vs B's deck (0-100)
) -> str:
    """Simulate a single game. Returns 'A' or 'B'."""
    return "A" if random.random() * 100 < wr_a else "B"


def simulate_conquest_series(
    lineup_a: list[dict],
    lineup_b: list[dict],
    matrix: dict,
    ban_a: str,
    ban_b: str,
) -> ConquestResult:
    """Simulate one full Conquest series (Bo5).

    Args:
        lineup_a/b: list of deck dicts with "name" field
        matrix: matrix[a_name][b_name] = winrate (0-100)
        ban_a: name of deck banned FROM lineup_b by player A
        ban_b: name of deck banned FROM lineup_a by player B
    """
    remaining_a = [d for d in lineup_a if d["name"] != ban_b]
    remaining_b = [d for d in lineup_b if d["name"] != ban_a]

    a_needs_win = {d["name"] for d in remaining_a}
    b_needs_win = {d["name"] for d in remaining_b}
    a_won_with = []
    b_won_with = []
    games = 0
    max_games = 15  # safety limit

    while a_needs_win and b_needs_win and games < max_games:
        # Strategic deck selection: pick deck with best avg WR vs opponent's remaining
        a_deck = _choose_deck(a_needs_win, b_needs_win, matrix, is_player_a=True)
        b_deck = _choose_deck(b_needs_win, a_needs_win, matrix, is_player_a=False)

        wr = matrix.get(a_deck, {}).get(b_deck, 50.0)
        winner = simulate_conquest_game(wr)
        games += 1

        if winner == "A":
            a_needs_win.discard(a_deck)
            a_won_with.append(a_deck)
        else:
            b_needs_win.discard(b_deck)
            b_won_with.append(b_deck)

    series_winner = "A" if not a_needs_win else "B"
    return ConquestResult(
        winner=series_winner, games_played=games,
        a_wins=a_won_with, b_wins=b_won_with,
        a_ban=ban_a, b_ban=ban_b,
    )


def _choose_deck(my_needs: set[str], opp_needs: set[str],
                  matrix: dict, is_player_a: bool) -> str:
    """Pick the deck with highest average WR vs opponent's remaining decks."""
    best_deck = None
    best_avg = -1
    for deck_name in my_needs:
        if is_player_a:
            avg_wr = sum(matrix.get(deck_name, {}).get(opp, 50.0)
                         for opp in opp_needs) / max(len(opp_needs), 1)
        else:
            avg_wr = sum(100 - matrix.get(opp, {}).get(deck_name, 50.0)
                         for opp in opp_needs) / max(len(opp_needs), 1)
        if avg_wr > best_avg:
            best_avg = avg_wr
            best_deck = deck_name
    return best_deck or (list(my_needs)[0] if my_needs else "")


def heuristic_ban(my_lineup: list[dict], opp_lineup: list[dict],
                  matrix: dict) -> str:
    """Ban the opponent's deck that beats us the most.

    For each opponent deck, compute its average winrate against our lineup.
    Ban the one with the highest average (= biggest threat to us).
    """
    worst_threat = None
    worst_avg = -1
    my_names = [d["name"] for d in my_lineup]

    for opp_deck in opp_lineup:
        opp_name = opp_deck["name"]
        # How well does this opp deck do against our lineup?
        avg_vs_us = sum(
            100 - matrix.get(my_name, {}).get(opp_name, 50.0)
            for my_name in my_names
        ) / max(len(my_names), 1)
        if avg_vs_us > worst_avg:
            worst_avg = avg_vs_us
            worst_threat = opp_name

    return worst_threat or opp_lineup[0]["name"]


def evaluate_lineup(
    lineup: list[dict],
    opponent_lineups: list[list[dict]],
    matrix: dict,
    num_sims: int = 200,
) -> float:
    """Evaluate a lineup's conquest winrate against multiple opponent lineups.

    Uses heuristic bans and simulates conquest series.
    Returns average series winrate (0.0 to 1.0).
    """
    if not opponent_lineups:
        return 0.5

    total_wins = 0
    total_series = 0

    for opp_lineup in opponent_lineups:
        ban_a = heuristic_ban(lineup, opp_lineup, matrix)
        ban_b = heuristic_ban(opp_lineup, lineup, matrix)

        wins = 0
        for _ in range(num_sims):
            result = simulate_conquest_series(lineup, opp_lineup, matrix, ban_a, ban_b)
            if result.winner == "A":
                wins += 1
            total_series += 1
        total_wins += wins

    return total_wins / max(total_series, 1)


def lineup_ban_resilience(
    lineup: list[dict],
    opp_field: list[dict],
    matrix: dict,
    num_sims: int = 100,
) -> float:
    """Score a lineup's worst-case scenario across all possible opponent bans.

    For each deck the opponent could ban from our lineup, compute our
    series winrate. Return the MINIMUM -- because the opponent will
    always find our weakest point.
    """
    worst_score = 1.0

    for banned_deck in lineup:
        remaining = [d for d in lineup if d is not banned_deck]
        # Simulate as if we only had 3 decks (already banned)
        total_wins = 0
        total = 0
        for opp in opp_field:
            opp_lineup = [opp]  # simplified: treat each opp deck as a 1-deck "lineup"
            # For proper evaluation, we'd need full opponent lineups
            # Simplified: compute remaining 3 decks' average WR vs this opp deck
            for my_deck in remaining:
                wr = matrix.get(my_deck["name"], {}).get(opp["name"], 50.0)
                total_wins += wr
                total += 100

        score = total_wins / max(total, 1)
        worst_score = min(worst_score, score)

    return worst_score
