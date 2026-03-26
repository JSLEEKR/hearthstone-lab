"""Tests for LadderOptimizer, LineupOptimizer, and conquest integration."""
import pytest
import random
from src.deckbuilder.ladder import LadderOptimizer, LadderResult
from src.deckbuilder.lineup import LineupOptimizer, LineupResult
from src.simulator.conquest import (
    simulate_conquest_series, heuristic_ban, evaluate_lineup,
    lineup_ban_resilience, ConquestResult,
)


@pytest.fixture
def sample_card_db():
    db = {}
    for i in range(60):
        db[f"c_{i}"] = {
            "card_id": f"c_{i}",
            "card_type": "MINION",
            "mana_cost": (i % 7) + 1,
            "attack": (i % 5) + 1,
            "health": (i % 5) + 2,
            "mechanics": [],
            "name": f"C{i}",
            "rarity": "COMMON",
            "hero_class": "NEUTRAL",
        }
    return db


@pytest.fixture
def four_class_decks():
    """Four decks from different classes."""
    classes = ["HUNTER", "WARRIOR", "MAGE", "PRIEST"]
    decks = []
    for i, cls in enumerate(classes):
        cards = [f"c_{(j + i * 10) % 60}" for j in range(15)] * 2
        decks.append({
            "name": f"{cls.title()} Deck",
            "hero": cls,
            "cards": cards,
            "archetype": "midrange",
            "fitness": 0.5 + i * 0.05,
        })
    return decks


@pytest.fixture
def matchup_matrix(four_class_decks):
    """A fabricated matchup matrix where higher-fitness decks beat lower ones."""
    matrix = {}
    for d in four_class_decks:
        matrix[d["name"]] = {}
        for opp in four_class_decks:
            if d["name"] == opp["name"]:
                continue
            # Higher fitness -> higher winrate
            diff = (d.get("fitness", 0.5) - opp.get("fitness", 0.5)) * 100
            wr = 50.0 + diff
            matrix[d["name"]][opp["name"]] = max(10, min(90, wr))
    return matrix


# ── Conquest module tests ──

class TestConquest:
    def test_simulate_conquest_series(self, four_class_decks, matchup_matrix):
        a = four_class_decks[:4]
        b = four_class_decks[:4]
        result = simulate_conquest_series(
            a, b, matchup_matrix,
            ban_a=b[0]["name"], ban_b=a[0]["name"],
        )
        assert isinstance(result, ConquestResult)
        assert result.winner in ("A", "B")
        assert result.games_played > 0

    def test_heuristic_ban(self, four_class_decks, matchup_matrix):
        lineup_a = four_class_decks[:4]
        lineup_b = four_class_decks[:4]
        ban = heuristic_ban(lineup_a, lineup_b, matchup_matrix)
        assert ban in [d["name"] for d in lineup_b]

    def test_evaluate_lineup(self, four_class_decks, matchup_matrix):
        lineup = four_class_decks[:4]
        opp_lineups = [four_class_decks[:4]]
        wr = evaluate_lineup(lineup, opp_lineups, matchup_matrix, num_sims=20)
        assert 0.0 <= wr <= 1.0

    def test_lineup_ban_resilience(self, four_class_decks, matchup_matrix):
        lineup = four_class_decks[:4]
        score = lineup_ban_resilience(lineup, four_class_decks, matchup_matrix,
                                       num_sims=10)
        assert 0.0 <= score <= 1.0


# ── Ladder Optimizer tests ──

class TestLadderOptimizer:
    def test_find_best_returns_result(self, sample_card_db, four_class_decks,
                                       matchup_matrix):
        opt = LadderOptimizer(
            card_db=sample_card_db,
            meta_field=four_class_decks,
            generations=0,  # skip mutation for speed
            matches_per_eval=1,
        )
        result = opt.find_best(four_class_decks, matchup_matrix)
        assert isinstance(result, LadderResult)
        assert result.best_deck
        assert "name" in result.best_deck
        assert result.meta_score > 0

    def test_find_best_empty_candidates(self, sample_card_db):
        opt = LadderOptimizer(card_db=sample_card_db, meta_field=[])
        result = opt.find_best([], {})
        assert result.meta_score == 0
        assert result.best_deck == {}

    def test_score_deck(self, sample_card_db, four_class_decks, matchup_matrix):
        opt = LadderOptimizer(
            card_db=sample_card_db,
            meta_field=four_class_decks,
        )
        score, details = opt._score_deck("Priest Deck", matchup_matrix)
        assert isinstance(score, float)
        assert len(details) == 3  # 4 decks minus self

    def test_bad_matchup_penalty(self, sample_card_db, four_class_decks):
        """A deck with sub-30% matchups gets penalised."""
        # Build a matrix with a terrible matchup
        matrix = {}
        deck = four_class_decks[0]
        for opp in four_class_decks:
            matrix.setdefault(deck["name"], {})[opp["name"]] = 50.0

        # Make one matchup terrible
        bad_opp = four_class_decks[1]["name"]
        matrix[deck["name"]][bad_opp] = 15.0

        opt = LadderOptimizer(
            card_db=sample_card_db,
            meta_field=four_class_decks,
            bad_matchup_penalty=5.0,
        )
        score_bad, _ = opt._score_deck(deck["name"], matrix)

        # Now fix it
        matrix[deck["name"]][bad_opp] = 50.0
        score_good, _ = opt._score_deck(deck["name"], matrix)

        assert score_good > score_bad

    def test_meta_weights(self, sample_card_db, four_class_decks, matchup_matrix):
        """Meta weights change the scoring."""
        opt_uniform = LadderOptimizer(
            card_db=sample_card_db,
            meta_field=four_class_decks,
        )
        opt_weighted = LadderOptimizer(
            card_db=sample_card_db,
            meta_field=four_class_decks,
            meta_weights={four_class_decks[0]["name"]: 10.0},
        )
        score_u, _ = opt_uniform._score_deck("Priest Deck", matchup_matrix)
        score_w, _ = opt_weighted._score_deck("Priest Deck", matchup_matrix)
        # With heavy weighting on one opponent, scores should differ
        assert score_u != score_w


# ── Lineup Optimizer tests ──

class TestLineupOptimizer:
    def test_find_best_lineup(self, sample_card_db, four_class_decks,
                               matchup_matrix):
        opt = LineupOptimizer(
            deck_pool=four_class_decks,
            matchup_matrix=matchup_matrix,
            card_db=sample_card_db,
            conquest_sims=10,
        )
        result = opt.find_best_lineup()
        assert isinstance(result, LineupResult)
        assert len(result.decks) == 4
        assert 0.0 <= result.conquest_winrate <= 1.0

    def test_fewer_classes_than_required(self, sample_card_db, matchup_matrix):
        """If only 2 classes available, should return what it can."""
        decks = [
            {"name": "D1", "hero": "MAGE", "cards": ["c_0"] * 30,
             "archetype": "aggro"},
            {"name": "D2", "hero": "HUNTER", "cards": ["c_1"] * 30,
             "archetype": "control"},
        ]
        opt = LineupOptimizer(
            deck_pool=decks,
            matchup_matrix=matchup_matrix,
            card_db=sample_card_db,
        )
        result = opt.find_best_lineup()
        assert isinstance(result, LineupResult)
        assert len(result.decks) <= 2

    def test_unique_classes(self, sample_card_db, four_class_decks,
                            matchup_matrix):
        """All decks in lineup should be different classes."""
        opt = LineupOptimizer(
            deck_pool=four_class_decks,
            matchup_matrix=matchup_matrix,
            card_db=sample_card_db,
            conquest_sims=10,
        )
        result = opt.find_best_lineup()
        heroes = [d["hero"] for d in result.decks]
        assert len(heroes) == len(set(heroes))

    def test_recommended_bans(self, sample_card_db, four_class_decks,
                               matchup_matrix):
        opp_lineups = [four_class_decks[:4]]
        opt = LineupOptimizer(
            deck_pool=four_class_decks,
            matchup_matrix=matchup_matrix,
            card_db=sample_card_db,
            conquest_sims=10,
        )
        result = opt.find_best_lineup(opponent_lineups=opp_lineups)
        assert isinstance(result.recommended_bans, dict)

    def test_five_classes_picks_four(self, sample_card_db, matchup_matrix):
        """With 5 classes, optimizer should still produce a 4-deck lineup."""
        classes = ["HUNTER", "WARRIOR", "MAGE", "PRIEST", "ROGUE"]
        decks = []
        for i, cls in enumerate(classes):
            cards = [f"c_{(j + i * 10) % 60}" for j in range(15)] * 2
            d = {
                "name": f"{cls.title()} Deck",
                "hero": cls,
                "cards": cards,
                "archetype": "midrange",
                "fitness": 0.5,
            }
            decks.append(d)
            # Add entries to matrix
            matchup_matrix.setdefault(d["name"], {})
            for opp in decks:
                if opp["name"] != d["name"]:
                    matchup_matrix[d["name"]][opp["name"]] = 50.0
                    matchup_matrix.setdefault(opp["name"], {})[d["name"]] = 50.0

        opt = LineupOptimizer(
            deck_pool=decks,
            matchup_matrix=matchup_matrix,
            card_db=sample_card_db,
            conquest_sims=10,
        )
        result = opt.find_best_lineup()
        assert len(result.decks) == 4
