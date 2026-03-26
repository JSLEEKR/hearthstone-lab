"""Full simulation and evolutionary optimization of 7 user-provided decks."""
import sys
import io
import json
import random
import copy
import time

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'C:/Users/user/OneDrive/Documents/hearthstone_deckmaker')

from src.core.deckstring import decode_deckstring
from src.db.database import SessionLocal
from src.db.tables import Card
from collections import Counter

print("=" * 80)
print("HEARTHSTONE DECK SIMULATION & EVOLUTIONARY OPTIMIZATION")
print("=" * 80)

# ──────────────────────────────────────────────────────────────────────────────
# STEP 1: Load decks from deckstrings
# ──────────────────────────────────────────────────────────────────────────────
print("\n[STEP 1] Loading 7 decks from deckstrings...\n")

db = SessionLocal()

deckstrings = [
    'AAECAaoICK+fBMODB9umB9+mB+WmB9C/B4LUB5vUBwv9nwTmlgf1rAexsAe8sQePvgfDwAfJwAf3wAf2wQfm/QcAAA==',
    'AAECAZICBKqBB5KDB/KDB6+HBw2HnwSunwSB1ATW+gbggQf3gQeIgwewhwekiQeYlweqrwesrwfXwAcAAA==',
    'AAECAZICAuDAB7HjBw6HnwTZnwSB1ASuhweSlweUlwfanQfgnQe4nwfJrAfWwAfXwAfbwAePwQcAAA==',
    'AAECAQcE0L8Hm8IHzskHm9QHDar8Bqv8BveDB+iHB8GPB9KXB+yyB4S9B4++B7XAB6/BB5zCB6DFBwAA',
    'AAECAR8GoPcGsYcHmacHmqcHm6cHxbEHDKmfBKqfBK+SB4WVB86bB+6fB5CnB5inB9SvB7TAB7nAB7vABwAA',
    'AAECAZ8FCvD+Bsj/BrSBB8ODB+6oB++oB/CoB/SqB+XBB6vGBwrJoATv/ga6lwebqQfLqQfErge+sgfiwQfowQfqwQcAAA==',
    'AAECAfHhBALtnweOvwcOhfYE1J4G1+UGyIwHupUHopcHvJoH0JsH0q0HhrEH4rEHiL8H/78HtcAHAAA=',
]

# Build card_db from ALL cards in DB
all_cards = db.query(Card).all()
card_db = {}
dbf_to_card_id = {}

for c in all_cards:
    mechs = c.mechanics or []
    if isinstance(mechs, str):
        mechs = [m.strip() for m in mechs.split(',') if m.strip()]

    race = ""
    jd = c.json_data
    if jd:
        if isinstance(jd, str):
            try:
                jd = json.loads(jd)
            except:
                jd = {}
        if isinstance(jd, dict):
            race = jd.get("race", "") or ""

    card_db[c.card_id] = {
        "card_id": c.card_id, "card_type": c.card_type or "MINION",
        "name": c.name or "", "mana_cost": c.mana_cost or 0,
        "attack": c.attack or 0, "health": c.health or 0,
        "durability": c.durability or 1, "mechanics": mechs,
        "text": c.text or "", "rarity": c.rarity or "",
        "hero_class": c.hero_class or "NEUTRAL", "race": race,
    }
    if c.dbf_id:
        dbf_to_card_id[c.dbf_id] = c.card_id

# Decode decks
decks = []
for i, ds in enumerate(deckstrings):
    result = decode_deckstring(ds)
    cards_dbf = result['cards']

    class_counts = Counter()
    card_ids_list = []
    missing_dbfs = []
    for dbf_id, count in cards_dbf.items():
        cid = dbf_to_card_id.get(dbf_id)
        if cid:
            card = card_db[cid]
            if card.get("hero_class") and card["hero_class"] != "NEUTRAL":
                class_counts[card["hero_class"]] += count
            for _ in range(count):
                card_ids_list.append(cid)
        else:
            missing_dbfs.append(dbf_id)

    hero_class = class_counts.most_common(1)[0][0] if class_counts else "NEUTRAL"

    if len(card_ids_list) < 30:
        fillers = [cid for cid, c in card_db.items()
                   if c.get("hero_class") in (hero_class, "NEUTRAL")
                   and c.get("card_type") in ("MINION", "SPELL")
                   and (c.get("mana_cost") or 0) <= 5]
        while len(card_ids_list) < 30 and fillers:
            card_ids_list.append(random.choice(fillers))

    class_map = {
        "DEATH_KNIGHT": "DK", "DEMON_HUNTER": "DH", "DRUID": "Druid",
        "HUNTER": "Hunter", "MAGE": "Mage", "PALADIN": "Paladin",
        "PRIEST": "Priest", "ROGUE": "Rogue", "SHAMAN": "Shaman",
        "WARLOCK": "Warlock", "WARRIOR": "Warrior",
    }
    class_short = class_map.get(hero_class, hero_class)
    name = f"User_{class_short}_{i+1}"

    decks.append({
        "name": name,
        "hero": hero_class,
        "cards": card_ids_list[:30],
        "archetype": "user",
        "missing": len(missing_dbfs),
    })

print(f"Loaded {len(decks)} decks:")
for d in decks:
    sample_names = []
    for cid in d["cards"][:5]:
        sample_names.append(card_db.get(cid, {}).get("name", cid)[:25])
    print(f"  {d['name']}: {d['hero']} ({len(d['cards'])} cards, {d['missing']} missing DBFs)")
    print(f"    Sample: {', '.join(sample_names)}")

# Save original decks for comparison
original_decks = []
for d in decks:
    original_decks.append({
        "name": d["name"],
        "hero": d["hero"],
        "cards": list(d["cards"]),
    })

# ──────────────────────────────────────────────────────────────────────────────
# STEP 2: Round-robin tournament (20 matches per pair)
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("[STEP 2] Round-Robin Tournament (20 matches per pair)")
print("=" * 80 + "\n")

from src.simulator.match import run_match

def run_round_robin(deck_list, matches_per_pair=20, label=""):
    """Run round-robin and return matchup matrix."""
    mat = {}
    for d in deck_list:
        mat[d["name"]] = {}

    total_pairs = len(deck_list) * (len(deck_list) - 1) // 2
    pair_count = 0

    for i, da in enumerate(deck_list):
        for j, d_b in enumerate(deck_list):
            if i >= j:
                continue
            pair_count += 1
            wins_a = 0
            games = 0
            for _ in range(matches_per_pair):
                try:
                    r = run_match(list(da["cards"]), list(d_b["cards"]),
                                  da["hero"], d_b["hero"], card_db, max_turns=60)
                    games += 1
                    if r.winner == "A":
                        wins_a += 1
                except:
                    pass

            wr = wins_a / max(games, 1) * 100
            mat[da["name"]][d_b["name"]] = wr
            mat[d_b["name"]][da["name"]] = 100 - wr
            print(f"  [{pair_count}/{total_pairs}] {da['name']} vs {d_b['name']}: "
                  f"{wr:.0f}% ({wins_a}/{games})")

    return mat

def print_matchup_table(deck_list, mat):
    """Print matchup table and rankings."""
    names = [d["name"] for d in deck_list]
    # Truncated names for header
    short = [n[-12:] for n in names]

    header = f"{'':>22}"
    for s in short:
        header += f" {s:>12}"
    header += "    AVG"
    print(header)
    print("-" * len(header))

    for d in deck_list:
        name = d["name"]
        wrs = [mat[name].get(d2["name"], 0) for d2 in deck_list if d2["name"] != name]
        avg_wr = sum(wrs) / max(len(wrs), 1)
        row = f"  {name:>20}"
        for d2 in deck_list:
            if d2["name"] == name:
                row += f" {'---':>12}"
            else:
                row += f" {mat[name].get(d2['name'], 0):11.0f}%"
        row += f"  {avg_wr:5.1f}%"
        print(row)

    # Rankings
    ranked = sorted(deck_list,
                    key=lambda d: sum(mat[d["name"]].values()) / max(len(mat[d["name"]]), 1),
                    reverse=True)
    print("\nRANKINGS:")
    for rank, d in enumerate(ranked, 1):
        name = d["name"]
        wrs = [mat[name].get(d2["name"], 0) for d2 in deck_list if d2["name"] != name]
        avg_wr = sum(wrs) / max(len(wrs), 1)
        print(f"  #{rank} {name} ({d['hero']}): {avg_wr:.1f}%")

start_time = time.time()
matrix = run_round_robin(decks, 20)
elapsed = time.time() - start_time
print(f"\nTournament completed in {elapsed:.1f}s\n")
print_matchup_table(decks, matrix)

# ──────────────────────────────────────────────────────────────────────────────
# STEP 3: Evolutionary optimization (per-deck, preserving all classes)
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("[STEP 3] Evolutionary Optimization (per-deck, 3 generations, 2 mutations)")
print("=" * 80 + "\n")

from src.deckbuilder.optimizer import DeckOptimizer, DeckGenome

def evolve_deck_against_field(deck, field, card_db, generations=3, mutations=2, matches=5):
    """Evolve a single deck against a fixed field of opponents.

    Returns the best version of this deck found.
    """
    best_cards = list(deck["cards"])
    best_wr = _eval_deck_vs_field(deck, field, card_db, matches)
    hero = deck["hero"]

    # Get available replacements for this class
    replacements = [cid for cid, c in card_db.items()
                    if c.get("hero_class") in (hero, "NEUTRAL")
                    and c.get("card_type") != "HERO"]

    print(f"  Evolving {deck['name']} (baseline WR: {best_wr:.1f}%)...")

    for gen in range(generations):
        # Try several mutations, keep the best
        candidates = []
        for _ in range(4):  # 4 candidates per generation
            new_cards = list(best_cards)
            for _ in range(mutations):
                if not new_cards or not replacements:
                    break
                remove_idx = random.randint(0, len(new_cards) - 1)
                new_cards.pop(remove_idx)
                for attempt in range(20):
                    rep = random.choice(replacements)
                    rarity = card_db.get(rep, {}).get("rarity", "")
                    max_copies = 1 if rarity == "LEGENDARY" else 2
                    if new_cards.count(rep) < max_copies:
                        new_cards.append(rep)
                        break
                else:
                    new_cards.append(random.choice(replacements))

            test_deck = dict(deck)
            test_deck["cards"] = new_cards
            wr = _eval_deck_vs_field(test_deck, field, card_db, matches)
            candidates.append((wr, new_cards))

        # Pick best candidate
        candidates.sort(key=lambda x: -x[0])
        if candidates[0][0] > best_wr:
            best_wr = candidates[0][0]
            best_cards = candidates[0][1]
            print(f"    Gen {gen+1}: improved to {best_wr:.1f}%")
        else:
            print(f"    Gen {gen+1}: no improvement (best={best_wr:.1f}%)")

    result = dict(deck)
    result["cards"] = best_cards
    result["fitness"] = best_wr / 100.0
    return result


def _eval_deck_vs_field(deck, field, card_db, matches_per_opp=5):
    """Evaluate a deck's winrate against a field of opponents."""
    wins = 0
    games = 0
    for opp in field:
        if opp["name"] == deck["name"]:
            continue
        for _ in range(matches_per_opp):
            try:
                r = run_match(list(deck["cards"]), list(opp["cards"]),
                              deck["hero"], opp["hero"], card_db, max_turns=60)
                games += 1
                if r.winner == "A":
                    wins += 1
            except:
                pass
    return (wins / max(games, 1)) * 100


evolved = []
for d in decks:
    # Evolve each deck against all OTHER decks
    field = [other for other in decks if other["name"] != d["name"]]
    ev = evolve_deck_against_field(d, field, card_db, generations=3, mutations=2, matches=5)
    evolved.append(ev)

print(f"\nEvolution complete. {len(evolved)} decks:\n")
for d in evolved:
    print(f"  {d['name']}: {d['hero']} fitness={d.get('fitness', 0):.3f}")

# ──────────────────────────────────────────────────────────────────────────────
# STEP 4: Re-run tournament with evolved decks
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("[STEP 4] Post-Evolution Tournament (20 matches per pair)")
print("=" * 80 + "\n")

start_time2 = time.time()
matrix2 = run_round_robin(evolved, 20)
elapsed2 = time.time() - start_time2
print(f"\nPost-evolution tournament completed in {elapsed2:.1f}s\n")
print_matchup_table(evolved, matrix2)

# ──────────────────────────────────────────────────────────────────────────────
# STEP 5: Ladder King and Championship Lineup
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("[STEP 5] Ladder King & Championship Lineup")
print("=" * 80 + "\n")

from src.deckbuilder.ladder import LadderOptimizer
from src.deckbuilder.lineup import LineupOptimizer

# Ladder King
ladder_opt = LadderOptimizer(
    card_db=card_db,
    meta_field=evolved,
    generations=3,
    matches_per_eval=5,
)
ladder_result = ladder_opt.find_best(evolved, matrix2)
print(f"LADDER KING: {ladder_result.best_deck.get('name', '?')} ({ladder_result.best_deck.get('hero', '?')})")
print(f"  Meta Score: {ladder_result.meta_score:.1f}%")
print(f"  Matchup Details:")
for opp_name, wr in sorted(ladder_result.matchup_details.items(), key=lambda x: -x[1]):
    print(f"    vs {opp_name}: {wr:.0f}%")

# Championship Lineup
print("\nSearching for best 4-deck Championship Lineup...")
lineup_opt = LineupOptimizer(
    deck_pool=evolved,
    matchup_matrix=matrix2,
    card_db=card_db,
    num_lineup_decks=4,
    conquest_sims=100,
)
lineup_result = lineup_opt.find_best_lineup()
print(f"\nCHAMPIONSHIP LINEUP (Conquest WR: {lineup_result.conquest_winrate:.1%}):")
print(f"  Ban Resilience: {lineup_result.ban_resilience:.1%}")
for d in lineup_result.decks:
    name = d["name"]
    avg = sum(matrix2.get(name, {}).values()) / max(len(matrix2.get(name, {})), 1)
    print(f"  - {name} ({d['hero']}) avg WR: {avg:.1f}%")

if lineup_result.recommended_bans:
    print(f"\n  Recommended Bans:")
    for opp_key, ban_name in list(lineup_result.recommended_bans.items())[:5]:
        print(f"    vs {opp_key}: ban {ban_name}")

# ──────────────────────────────────────────────────────────────────────────────
# STEP 6: Before/After Card Changes
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("[STEP 6] Card Changes (Original vs Evolved)")
print("=" * 80 + "\n")

for i, d in enumerate(evolved):
    orig = original_decks[i]

    orig_set = Counter(orig["cards"])
    evol_set = Counter(d["cards"])

    removed = orig_set - evol_set
    added = evol_set - orig_set

    if not removed and not added:
        print(f"{d['name']} ({d['hero']}): UNCHANGED")
    else:
        pre_wr = sum(matrix.get(orig["name"], {}).values()) / max(len(matrix.get(orig["name"], {})), 1)
        post_wr = sum(matrix2.get(d["name"], {}).values()) / max(len(matrix2.get(d["name"], {})), 1)
        delta = post_wr - pre_wr
        print(f"{d['name']} ({d['hero']}): WR {pre_wr:.1f}% -> {post_wr:.1f}% ({'+' if delta >= 0 else ''}{delta:.1f}%)")
        if removed:
            print(f"  REMOVED ({sum(removed.values())} cards):")
            for cid, cnt in removed.most_common():
                cname = card_db.get(cid, {}).get("name", cid)
                cost = card_db.get(cid, {}).get("mana_cost", "?")
                print(f"    - {cnt}x [{cost} mana] {cname}")
        if added:
            print(f"  ADDED ({sum(added.values())} cards):")
            for cid, cnt in added.most_common():
                cname = card_db.get(cid, {}).get("name", cid)
                cost = card_db.get(cid, {}).get("mana_cost", "?")
                print(f"    + {cnt}x [{cost} mana] {cname}")
    print()

# ──────────────────────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ──────────────────────────────────────────────────────────────────────────────
print("=" * 80)
print("FINAL SUMMARY")
print("=" * 80)

# Before/after comparison
print("\nDeck Performance (Before -> After Evolution):")
for i, d in enumerate(evolved):
    orig_name = original_decks[i]["name"]
    pre_wr = sum(matrix.get(orig_name, {}).values()) / max(len(matrix.get(orig_name, {})), 1)
    post_wr = sum(matrix2.get(d["name"], {}).values()) / max(len(matrix2.get(d["name"], {})), 1)
    delta = post_wr - pre_wr
    marker = "^" if delta > 2 else ("v" if delta < -2 else "=")
    print(f"  {marker} {d['name']:>25} ({d['hero']:>12}): {pre_wr:5.1f}% -> {post_wr:5.1f}% ({'+' if delta >= 0 else ''}{delta:.1f}%)")

print(f"\nLadder King: {ladder_result.best_deck.get('name', '?')} (Meta Score: {ladder_result.meta_score:.1f}%)")
print(f"Championship Lineup ({lineup_result.conquest_winrate:.1%} Conquest WR):")
for d in lineup_result.decks:
    print(f"  - {d['name']} ({d['hero']})")

total_time = time.time() - start_time
print(f"\nTotal runtime: {total_time:.1f}s")
print("=" * 80)

db.close()
