"""Card-specific effect handlers for legendary minions."""
from __future__ import annotations
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.simulator.engine import GameEngine
    from src.simulator.game_state import GameState, PlayerState, MinionState

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _draw_cards(player, n):
    for _ in range(n):
        player.draw_card()


def _summon_token(player, name, atk, hp, **kw):
    from src.simulator.game_state import MinionState, BOARD_LIMIT
    if len(player.board) < BOARD_LIMIT:
        player.board.append(MinionState(
            card_id=f"token_{name}", name=name,
            attack=atk, health=hp, max_health=hp,
            mana_cost=0, summoned_this_turn=True, **kw,
        ))


def _random_minion_from_db(engine, cost=None):
    candidates = [c for c in engine.card_db.values()
                  if c.get("card_type") == "MINION"
                  and not c.get("card_id", "").startswith("token_")
                  and not c.get("card_id", "").endswith("_mini")]
    if cost is not None:
        filtered = [c for c in candidates if c.get("mana_cost") == cost]
        if filtered:
            candidates = filtered
    return random.choice(candidates) if candidates else None


def _get_opponent(state, player):
    """Return the opponent PlayerState."""
    return state.player2 if player is state.player1 else state.player1


def _deal_damage_to_all_enemies(state, player, damage):
    """Deal *damage* to opponent hero and all opponent minions."""
    opp = _get_opponent(state, player)
    opp.hero.take_damage(damage)
    for m in list(opp.board):
        m.take_damage(damage)


# ---------------------------------------------------------------------------
# DEATHKNIGHT
# ---------------------------------------------------------------------------

def _buttons(engine, state, player, minion):
    """VAC_437 Buttons: draw 3 cards."""
    _draw_cards(player, 3)


def _exarch_maladaar(engine, state, player, minion):
    """GDB_470 Exarch Maladaar: give player 3 extra mana this turn."""
    player.mana += 3


def _high_cultist_herenn(engine, state, player, minion):
    """TLC_810 High Cultist Herenn: Summon 2 Deathrattle minions from your deck. They fight!"""
    from src.simulator.game_state import MinionState, BOARD_LIMIT
    pulled = []
    for i, card_id in enumerate(list(player.deck)):
        card = engine.card_db.get(card_id, {})
        if card.get("card_type") == "MINION" and "DEATHRATTLE" in card.get("mechanics", []):
            pulled.append((i, card_id, card))
            if len(pulled) >= 2:
                break
    summoned = []
    # Remove from deck in reverse order to preserve indices
    for idx, card_id, card in reversed(pulled):
        player.deck.pop(idx)
    for _, card_id, card in pulled:
        if len(player.board) < BOARD_LIMIT:
            m = MinionState(
                card_id=card_id, name=card.get("name", "Minion"),
                attack=card.get("attack", 1), health=card.get("health", 1),
                max_health=card.get("health", 1), mana_cost=card.get("mana_cost", 0),
                mechanics=list(card.get("mechanics", [])),
                summoned_this_turn=True,
            )
            player.board.append(m)
            summoned.append(m)
    # They fight each other
    if len(summoned) == 2:
        a, b = summoned
        a.take_damage(b.attack)
        b.take_damage(a.attack)


# ---------------------------------------------------------------------------
# DEMONHUNTER
# ---------------------------------------------------------------------------

def _kayn_sunfury(engine, state, player, minion):
    """CORE_BT_187 Kayn Sunfury: charge (attacks ignore taunt simplified)."""
    minion.charge = True


def _xortoth(engine, state, player, minion):
    """GDB_118 Xor'toth: deal 5 damage to all enemies."""
    _deal_damage_to_all_enemies(state, player, 5)


def _aranna_thrill_seeker(engine, state, player, minion):
    """VAC_501 Aranna Thrill Seeker: damage to hero redirected to random enemy.
    Simplified: gain 5 armor (damage reduction equivalent)."""
    player.hero.armor += 5


def _entomologist_toru(engine, state, player, minion):
    """TLC_841 Entomologist Toru: set all hand card costs to 1."""
    for card_id in player.hand:
        card = engine.card_db.get(card_id, {})
        if card:
            card["mana_cost"] = 1


# ---------------------------------------------------------------------------
# DRUID
# ---------------------------------------------------------------------------

def _exarch_othaar(engine, state, player, minion):
    """GDB_856 Exarch Othaar: draw 3 cards, reduce their cost by 2."""
    for _ in range(3):
        drawn = player.draw_card()
        if drawn:
            card = engine.card_db.get(drawn, {})
            if card:
                card["mana_cost"] = max(0, card.get("mana_cost", 0) - 2)


def _fandral_staghelm(engine, state, player, minion):
    """CORE_OG_044 Fandral Staghelm: Choose One cards have both effects.
    Simplified: give +2/+2 to the minion itself as value representation."""
    minion.attack += 2
    minion.health += 2
    minion.max_health += 2


def _ulfar(engine, state, player, minion):
    """CORE_CATA_006 Ulfar: +2/+2 to all other friendly minions."""
    for m in player.board:
        if m is not minion:
            m.attack += 2
            m.health += 2
            m.max_health += 2


# ---------------------------------------------------------------------------
# HUNTER
# ---------------------------------------------------------------------------

def _halazzi(engine, state, player, minion):
    """CORE_TRL_900 Halazzi: fill hand with 1/1 rush tokens."""
    from src.simulator.game_state import HAND_LIMIT
    while len(player.hand) < HAND_LIMIT:
        player.hand.append("token_Lynx")
        # Register token in card_db so AI can play it
        if "token_Lynx" not in engine.card_db:
            engine.card_db["token_Lynx"] = {
                "card_id": "token_Lynx", "name": "Lynx", "card_type": "MINION",
                "attack": 1, "health": 1, "mana_cost": 0,
                "mechanics": ["RUSH"],
            }


def _king_maluk(engine, state, player, minion):
    """TIME_042 King Maluk: Discard your hand. Get Infinite Bananas."""
    from src.simulator.game_state import HAND_LIMIT
    player.hand.clear()
    # Register banana token
    if "token_Banana" not in engine.card_db:
        engine.card_db["token_Banana"] = {
            "card_id": "token_Banana", "name": "Banana", "card_type": "SPELL",
            "mana_cost": 1, "text": "Give a minion +1/+1.",
            "mechanics": [],
        }
    while len(player.hand) < HAND_LIMIT:
        player.hand.append("token_Banana")


def _king_plush(engine, state, player, minion):
    """TOY_357 King Plush: return enemy minions with less attack to opponent's deck."""
    opp = _get_opponent(state, player)
    returned = [m for m in opp.board if m.attack < minion.attack]
    for m in returned:
        opp.board.remove(m)
        opp.deck.append(m.card_id)
    random.shuffle(opp.deck)


# ---------------------------------------------------------------------------
# MAGE
# ---------------------------------------------------------------------------

def _puzzlemaster_khadgar(engine, state, player, minion):
    """TOY_373 Puzzlemaster Khadgar: Equip a 0/6 Orb of Wisdom."""
    from src.simulator.game_state import WeaponState
    player.hero.weapon = WeaponState(
        card_id="token_Orb_of_Wisdom", name="Orb of Wisdom",
        attack=0, durability=6,
    )


def _portalmancer_skyla(engine, state, player, minion):
    """WORK_063 Portalmancer Skyla: reduce a spell cost by 3."""
    for card_id in player.hand:
        card = engine.card_db.get(card_id, {})
        if card.get("card_type") == "SPELL":
            card["mana_cost"] = max(0, card.get("mana_cost", 0) - 3)
            break


def _aessina(engine, state, player, minion):
    """EDR_430 Aessina: if 20+ friendly minions died, deal 20 randomly to enemies."""
    if player.friendly_deaths_this_game >= 20:
        opp = _get_opponent(state, player)
        targets = list(opp.board) + [opp.hero]
        for _ in range(20):
            if not targets:
                break
            t = random.choice(targets)
            t.take_damage(1)
            # Remove dead minions from target list
            targets = [x for x in targets if not getattr(x, "is_dead", False)]


# ---------------------------------------------------------------------------
# NEUTRAL
# ---------------------------------------------------------------------------

def _zilliax(engine, state, player, minion):
    """TOY_330 Zilliax Deluxe 3000: default modules — rush + divine shield."""
    minion.rush = True
    minion.divine_shield = True
    if "RUSH" not in minion.mechanics:
        minion.mechanics.append("RUSH")
    if "DIVINE_SHIELD" not in minion.mechanics:
        minion.mechanics.append("DIVINE_SHIELD")


def _brightwing(engine, state, player, minion):
    """CORE_EX1_189 Brightwing: add random legendary to hand."""
    from src.simulator.game_state import HAND_LIMIT
    legendaries = [c for c in engine.card_db.values()
                   if c.get("rarity") == "LEGENDARY" and c.get("card_type") == "MINION"]
    if legendaries and len(player.hand) < HAND_LIMIT:
        chosen = random.choice(legendaries)
        player.hand.append(chosen.get("card_id", ""))


def _king_mukla(engine, state, player, minion):
    """CORE_EX1_014 King Mukla: Give your opponent 2 Bananas."""
    from src.simulator.game_state import HAND_LIMIT
    opp = _get_opponent(state, player)
    if "token_Banana" not in engine.card_db:
        engine.card_db["token_Banana"] = {
            "card_id": "token_Banana", "name": "Banana", "card_type": "SPELL",
            "mana_cost": 1, "text": "Give a minion +1/+1.",
            "mechanics": [],
        }
    for _ in range(2):
        if len(opp.hand) < HAND_LIMIT:
            opp.hand.append("token_Banana")


def _egg_of_khelos(engine, state, player, minion):
    """DINO_410 Egg of Khelos: summon a 0/3 token."""
    _summon_token(player, "Egg", 0, 3)


def _gorgonzormu(engine, state, player, minion):
    """VAC_955 Gorgonzormu: draw 1."""
    player.draw_card()


def _black_knight(engine, state, player, minion):
    """CORE_EX1_002 Black Knight: destroy an enemy taunt minion."""
    opp = _get_opponent(state, player)
    taunts = [m for m in opp.board if m.taunt]
    if taunts:
        target = random.choice(taunts)
        target.health = 0


def _tindral_sageswift(engine, state, player, minion):
    """FIR_958 Tindral Sageswift: deathrattle deal 1 to all enemies (4 on opponent's turn).
    Register deathrattle text so engine can parse it."""
    if "DEATHRATTLE" not in minion.mechanics:
        minion.mechanics.append("DEATHRATTLE")
    # Register parseable deathrattle text in card_db
    engine.card_db[minion.card_id] = engine.card_db.get(minion.card_id, {})
    engine.card_db[minion.card_id]["text"] = "죽음의 메아리: 모든 적 하수인에게 피해를 2 줍니다"


def _elise_the_navigator(engine, state, player, minion):
    """TLC_100 Elise the Navigator: If starting deck had 10 different costs, Craft a Location.
    Simplified: summon a 0/3 taunt token representing the location."""
    _summon_token(player, "Map Location", 0, 3, taunt=True)


def _torga(engine, state, player, minion):
    """TLC_102 Torga: draw 2."""
    _draw_cards(player, 2)


def _splendiferous_whizbang(engine, state, player, minion):
    """TOY_700 Splendiferous Whizbang: stat body only."""
    pass


def _the_curator(engine, state, player, minion):
    """CORE_KAR_061 The Curator: draw 3 cards."""
    _draw_cards(player, 3)


def _taelan_fordring(engine, state, player, minion):
    """CS3_024 Taelan Fordring: deathrattle draw 1 (simplified)."""
    if "DEATHRATTLE" not in minion.mechanics:
        minion.mechanics.append("DEATHRATTLE")
    player.draw_card()


def _vyranoth(engine, state, player, minion):
    """CATA_213 Vyranoth: +2/+2 to all hand minions."""
    for card_id in player.hand:
        card = engine.card_db.get(card_id, {})
        if card.get("card_type") == "MINION":
            card["attack"] = card.get("attack", 0) + 2
            card["health"] = card.get("health", 0) + 2


def _ultraxion(engine, state, player, minion):
    """CATA_497 Ultraxion: reduce a card cost by 3."""
    for card_id in player.hand:
        card = engine.card_db.get(card_id, {})
        if card:
            card["mana_cost"] = max(0, card.get("mana_cost", 0) - 3)
            break


def _chromie(engine, state, player, minion):
    """TIME_103 Chromie: draw 3."""
    _draw_cards(player, 3)


def _warmaster_blackhorn(engine, state, player, minion):
    """CATA_720 Warmaster Blackhorn: destroy all cards costing 2 or less in both decks."""
    opp = _get_opponent(state, player)
    player.deck = [c for c in player.deck
                   if engine.card_db.get(c, {}).get("mana_cost", 0) > 2]
    opp.deck = [c for c in opp.deck
                if engine.card_db.get(c, {}).get("mana_cost", 0) > 2]


def _the_exodar(engine, state, player, minion):
    """GDB_120 The Exodar: summon a 5/5 token."""
    _summon_token(player, "Draenei", 5, 5)


def _velen(engine, state, player, minion):
    """GDB_131 Velen: Deathrattle: trigger all Battlecries and Deathrattles of other Draenei.
    Ensure DEATHRATTLE mechanic is set. Approximation: deal 3 to all enemies + draw 2."""
    if "DEATHRATTLE" not in minion.mechanics:
        minion.mechanics.append("DEATHRATTLE")
    _draw_cards(player, 2)
    _deal_damage_to_all_enemies(state, player, 3)


def _endbringer_umbra(engine, state, player, minion):
    """TLC_106 Endbringer Umbra: deal 5 damage to random enemies."""
    opp = _get_opponent(state, player)
    for _ in range(5):
        targets = list(opp.board) + [opp.hero]
        if targets:
            random.choice(targets).take_damage(1)


def _mayor_noggenfogger(engine, state, player, minion):
    """CORE_CFM_670 Mayor Noggenfogger: All targets are chosen randomly.
    Simplified: give all friendly minions the FORGETFUL mechanic."""
    for m in player.board:
        if "FORGETFUL" not in m.mechanics:
            m.mechanics.append("FORGETFUL")


def _avatar_of_hearthstone(engine, state, player, minion):
    """CORE_WON_145 Avatar of Hearthstone: add 5 random cards to hand."""
    from src.simulator.game_state import HAND_LIMIT
    all_cards = list(engine.card_db.keys())
    all_cards = [c for c in all_cards
                 if not c.startswith("token_") and not c.endswith("_mini")]
    for _ in range(5):
        if len(player.hand) >= HAND_LIMIT or not all_cards:
            break
        player.hand.append(random.choice(all_cards))


def _endtime_murozond(engine, state, player, minion):
    """END_037 Endtime Murozond: fill board with random dragons, full heal hero."""
    from src.simulator.game_state import BOARD_LIMIT
    dragons = [c for c in engine.card_db.values()
               if c.get("card_type") == "MINION" and "DRAGON" in c.get("races", [])]
    while len(player.board) < BOARD_LIMIT:
        if dragons:
            d = random.choice(dragons)
            _summon_token(player, d.get("name", "Dragon"),
                          d.get("attack", 3), d.get("health", 3))
        else:
            _summon_token(player, "Dragon", 4, 4)
    player.hero.health = player.hero.max_health


def _travelmaster_dungar(engine, state, player, minion):
    """WORK_043 Travelmaster Dungar: Summon 3 minions from different expansions from your deck."""
    from src.simulator.game_state import MinionState, BOARD_LIMIT
    pulled = []
    for i, card_id in enumerate(list(player.deck)):
        card = engine.card_db.get(card_id, {})
        if card.get("card_type") == "MINION":
            pulled.append((i, card_id, card))
            if len(pulled) >= 3:
                break
    for idx, card_id, card in reversed(pulled):
        player.deck.pop(idx)
    for _, card_id, card in pulled:
        if len(player.board) < BOARD_LIMIT:
            m = MinionState(
                card_id=card_id, name=card.get("name", "Minion"),
                attack=card.get("attack", 1), health=card.get("health", 1),
                max_health=card.get("health", 1), mana_cost=card.get("mana_cost", 0),
                mechanics=list(card.get("mechanics", [])),
                summoned_this_turn=True,
            )
            player.board.append(m)


# ---------------------------------------------------------------------------
# PALADIN
# ---------------------------------------------------------------------------

def _toreth(engine, state, player, minion):
    """EDR_258 Toreth: stat body + divine shield (already has DIVINE_SHIELD)."""
    minion.divine_shield = True


def _toy_captain_tarim(engine, state, player, minion):
    """TOY_813 Toy Captain Tarim: set all enemy minions to 3/3."""
    opp = _get_opponent(state, player)
    for m in opp.board:
        m.attack = 3
        m.health = 3
        m.max_health = 3


def _tirion_fordring(engine, state, player, minion):
    """CORE_EX1_383 Tirion Fordring: deathrattle equip 5/3 Ashbringer weapon.
    Register deathrattle in card_db for engine parsing. Also handle via
    special deathrattle: on death, equip weapon directly."""
    if "DEATHRATTLE" not in minion.mechanics:
        minion.mechanics.append("DEATHRATTLE")
    # Register a custom deathrattle handler by setting text the parser can't handle,
    # so we store the weapon equip intent. The actual equip happens in remove_dead_minions
    # via a special card_db flag.
    db_entry = dict(engine.card_db.get(minion.card_id, {}))
    db_entry["_deathrattle_weapon"] = {"card_id": "tirion_ashbringer", "name": "Ashbringer", "attack": 5, "durability": 3}
    engine.card_db[minion.card_id] = db_entry


def _ursol(engine, state, player, minion):
    """EDR_259 Ursol: deal 5 damage to all enemies."""
    _deal_damage_to_all_enemies(state, player, 5)


# ---------------------------------------------------------------------------
# PRIEST
# ---------------------------------------------------------------------------

def _chillin_voljin(engine, state, player, minion):
    """VAC_957 Chillin Vol'jin: swap highest enemy with lowest friendly stats."""
    opp = _get_opponent(state, player)
    if opp.board and player.board:
        highest_enemy = max(opp.board, key=lambda m: m.attack + m.health)
        lowest_friendly = min(player.board, key=lambda m: m.attack + m.health)
        (highest_enemy.attack, lowest_friendly.attack) = (lowest_friendly.attack, highest_enemy.attack)
        (highest_enemy.health, lowest_friendly.health) = (lowest_friendly.health, highest_enemy.health)
        (highest_enemy.max_health, lowest_friendly.max_health) = (lowest_friendly.max_health, highest_enemy.max_health)


def _narain_soothfancy(engine, state, player, minion):
    """VAC_420 Narain Soothfancy: Get 2 Prophecies that become your next cards.
    Simplified: generate 2 random cards and add to hand."""
    from src.simulator.game_state import HAND_LIMIT
    for _ in range(2):
        if len(player.hand) >= HAND_LIMIT:
            break
        card = _random_minion_from_db(engine)
        if card:
            player.hand.append(card.get("card_id", ""))


def _timewinder_zarimi(engine, state, player, minion):
    """TOY_385 Timewinder Zarimi: If you've played 8 other Dragons, take an extra turn.
    Approximation: if 8+ cards played this game, give all friendly minions windfury."""
    total_played = player.cards_played_this_turn + state.turn  # rough estimate of total cards played
    if total_played >= 8:
        for m in player.board:
            m.windfury = True


def _eternus(engine, state, player, minion):
    """TIME_435 Eternus: steal enemy minion with health <= 2."""
    from src.simulator.game_state import BOARD_LIMIT
    opp = _get_opponent(state, player)
    targets = [m for m in opp.board if m.health <= minion.health]
    if targets and len(player.board) < BOARD_LIMIT:
        stolen = random.choice(targets)
        opp.board.remove(stolen)
        player.board.append(stolen)


def _natalie_seline(engine, state, player, minion):
    """CORE_EX1_198 Natalie Seline: destroy a minion, gain its health."""
    opp = _get_opponent(state, player)
    if opp.board:
        target = random.choice(opp.board)
        gained = target.health
        target.health = 0
        minion.health += gained
        minion.max_health += gained


def _tyrande(engine, state, player, minion):
    """EDR_464 Tyrande: Your next 3 spells are cast twice.
    Approximation: give +3 spell power via SPELLPOWER mechanic."""
    if "SPELLPOWER" not in minion.mechanics:
        minion.mechanics.append("SPELLPOWER")
    # Register spell power +3 in card_db text so _get_spell_power parses it
    db_entry = dict(engine.card_db.get(minion.card_id, {}))
    db_entry["text"] = db_entry.get("text", "") + " 주문 공격력 +3"
    engine.card_db[minion.card_id] = db_entry


# ---------------------------------------------------------------------------
# ROGUE
# ---------------------------------------------------------------------------

def _mirrex(engine, state, player, minion):
    """DINO_407 Mirrex: summon a copy of random enemy minion."""
    from src.simulator.game_state import MinionState, BOARD_LIMIT
    opp = _get_opponent(state, player)
    if opp.board and len(player.board) < BOARD_LIMIT:
        src = random.choice(opp.board)
        copy = MinionState(
            card_id=src.card_id, name=src.name,
            attack=src.attack, health=src.health, max_health=src.max_health,
            mana_cost=src.mana_cost, taunt=src.taunt,
            divine_shield=src.divine_shield, stealth=src.stealth,
            windfury=src.windfury, lifesteal=src.lifesteal,
            poisonous=src.poisonous, reborn=src.reborn,
            rush=src.rush, charge=src.charge,
            mechanics=list(src.mechanics), summoned_this_turn=True,
        )
        player.board.append(copy)


def _opu_the_unseen(engine, state, player, minion):
    """TLC_522 Opu the Unseen: deal 1 to all enemies, draw 1."""
    _deal_damage_to_all_enemies(state, player, 1)
    player.draw_card()


# ---------------------------------------------------------------------------
# SHAMAN
# ---------------------------------------------------------------------------

def _bralma_searstone(engine, state, player, minion):
    """TLC_228 Bralma Searstone: aura — elemental cards deal +1 damage.
    Simplified as spell power +1 (functionally equivalent for simulation)."""
    if "SPELLPOWER" not in minion.mechanics:
        minion.mechanics.append("SPELLPOWER")


def _farseer_nobundo(engine, state, player, minion):
    """GDB_447 Farseer Nobundo: deathrattle draw 1 (simplified)."""
    if "DEATHRATTLE" not in minion.mechanics:
        minion.mechanics.append("DEATHRATTLE")
    player.draw_card()


def _kragwa(engine, state, player, minion):
    """CORE_TRL_345 Krag'wa: Return all spells you cast last turn to your hand.
    We can't track last turn's spells; draw 2 as average approximation."""
    _draw_cards(player, 2)


def _shudderblock(engine, state, player, minion):
    """TOY_501 Shudderblock: Your next Battlecry triggers 3 times.
    Approximation: give the player 3 extra mana (representing 3x battlecry value)."""
    player.mana += 3


def _murmur(engine, state, player, minion):
    """GDB_448 Murmur: reduce all hand minion costs by 3."""
    for card_id in player.hand:
        card = engine.card_db.get(card_id, {})
        if card.get("card_type") == "MINION":
            card["mana_cost"] = max(0, card.get("mana_cost", 0) - 3)


# ---------------------------------------------------------------------------
# WARLOCK
# ---------------------------------------------------------------------------

def _razidir(engine, state, player, minion):
    """TLC_463 Razidir: discard 1, draw 1."""
    if player.hand:
        player.hand.pop(random.randrange(len(player.hand)))
    player.draw_card()


def _game_master_nemsy(engine, state, player, minion):
    """TOY_524 Game Master Nemsy: draw a demon (simplified: draw 1)."""
    player.draw_card()


def _archimonde(engine, state, player, minion):
    """GDB_128 Archimonde: Summon all Demons you played this game that didn't start in your deck.
    Approximation: summon 3 random 6/6 demon tokens (mid-to-late game demons)."""
    for _ in range(3):
        _summon_token(player, "Demon", 6, 6)


def _party_planner_vona(engine, state, player, minion):
    """VAC_945 Party Planner Vona: If you took 8 damage on your turn, summon Ouroboros (8/8).
    Check if player hero health < 22 (lost 8+ HP) as approximation."""
    if player.hero.health + player.hero.armor < 22:
        _summon_token(player, "Ouroboros", 8, 8)


def _agamaggan(engine, state, player, minion):
    """EDR_489 Agamaggan: gain 5 extra mana."""
    player.mana += 5


# ---------------------------------------------------------------------------
# CARD_HANDLERS registry  (card_id -> handler function)
# ---------------------------------------------------------------------------

CARD_HANDLERS = {
    # DEATHKNIGHT
    "VAC_437": _buttons,
    "GDB_470": _exarch_maladaar,
    "TLC_810": _high_cultist_herenn,

    # DEMONHUNTER
    "CORE_BT_187": _kayn_sunfury,
    "GDB_118": _xortoth,
    "VAC_501": _aranna_thrill_seeker,
    "TLC_841": _entomologist_toru,

    # DRUID
    "GDB_856": _exarch_othaar,
    "CORE_OG_044": _fandral_staghelm,
    "CORE_CATA_006": _ulfar,

    # HUNTER
    "CORE_TRL_900": _halazzi,
    "TIME_042": _king_maluk,
    "TOY_357": _king_plush,

    # MAGE
    "TOY_373": _puzzlemaster_khadgar,
    "WORK_063": _portalmancer_skyla,
    "EDR_430": _aessina,

    # NEUTRAL
    "TOY_330": _zilliax,
    "CORE_EX1_189": _brightwing,
    "CORE_EX1_014": _king_mukla,
    "DINO_410": _egg_of_khelos,
    "VAC_955": _gorgonzormu,
    "CORE_EX1_002": _black_knight,
    "FIR_958": _tindral_sageswift,
    "TLC_100": _elise_the_navigator,
    "TLC_102": _torga,
    "TOY_700": _splendiferous_whizbang,
    "CORE_KAR_061": _the_curator,
    "CS3_024": _taelan_fordring,
    "CATA_213": _vyranoth,
    "CATA_497": _ultraxion,
    "TIME_103": _chromie,
    "CATA_720": _warmaster_blackhorn,
    "GDB_120": _the_exodar,
    "GDB_131": _velen,
    "TLC_106": _endbringer_umbra,
    "CORE_CFM_670": _mayor_noggenfogger,
    "CORE_WON_145": _avatar_of_hearthstone,
    "END_037": _endtime_murozond,
    "WORK_043": _travelmaster_dungar,

    # PALADIN
    "EDR_258": _toreth,
    "TOY_813": _toy_captain_tarim,
    "CORE_EX1_383": _tirion_fordring,
    "EDR_259": _ursol,

    # PRIEST
    "VAC_957": _chillin_voljin,
    "VAC_420": _narain_soothfancy,
    "TOY_385": _timewinder_zarimi,
    "TIME_435": _eternus,
    "CORE_EX1_198": _natalie_seline,
    "EDR_464": _tyrande,

    # ROGUE
    "DINO_407": _mirrex,
    "TLC_522": _opu_the_unseen,

    # SHAMAN
    "TLC_228": _bralma_searstone,
    "GDB_447": _farseer_nobundo,
    "CORE_TRL_345": _kragwa,
    "TOY_501": _shudderblock,
    "GDB_448": _murmur,

    # WARLOCK
    "TLC_463": _razidir,
    "TOY_524": _game_master_nemsy,
    "GDB_128": _archimonde,
    "VAC_945": _party_planner_vona,
    "EDR_489": _agamaggan,
}


# ---------------------------------------------------------------------------
# TITAN HANDLERS
# Each receives (engine, state, player, minion, ability_idx) where ability_idx is 0, 1, or 2.
# ---------------------------------------------------------------------------

def _titan_primus(engine, state, player, minion, idx):
    """TTN_737 The Primus (DK): 0=Deal 5 dmg to minion, 1=Destroy a minion + summon 2/2 taunt, 2=Equip 3/3 lifesteal weapon"""
    opp = _get_opponent(state, player)
    if idx == 0:
        if opp.board:
            target = max(opp.board, key=lambda m: m.health)
            target.take_damage(5)
            target.frozen = True
    elif idx == 1:
        if opp.board:
            target = max(opp.board, key=lambda m: m.health)
            target.health = 0
            _summon_token(player, "Undead", 2, 2, taunt=True)
    elif idx == 2:
        from src.simulator.game_state import WeaponState
        player.hero.weapon = WeaponState("primus_staff", "Staff of the Primus", 3, 3)


def _titan_argus(engine, state, player, minion, idx):
    """TTN_862 Argus (DH): 0=Reduce random hand card cost by 3, 1=Gain 5 armor, 2=Deal 3 to all enemy minions"""
    opp = _get_opponent(state, player)
    if idx == 0:
        if player.hand:
            card_id = random.choice(player.hand)
            cd = engine.card_db.get(card_id, {})
            if cd:
                cd["mana_cost"] = max(0, cd.get("mana_cost", 0) - 3)
    elif idx == 1:
        player.hero.armor += 5
    elif idx == 2:
        for m in list(opp.board):
            m.take_damage(3)


def _titan_eonar(engine, state, player, minion, idx):
    """TTN_903 Eonar (Druid): 0=+2/+2 to other minions, 1=Restore 10 HP, 2=Summon two 5/5 taunts"""
    if idx == 0:
        for m in player.board:
            if m is not minion:
                m.attack += 2
                m.health += 2
                m.max_health += 2
    elif idx == 1:
        player.hero.health = min(player.hero.health + 10, player.hero.max_health)
    elif idx == 2:
        _summon_token(player, "Ancient", 5, 5, taunt=True)
        _summon_token(player, "Ancient", 5, 5, taunt=True)


def _titan_aggramar(engine, state, player, minion, idx):
    """TTN_092 Aggramar (Hunter): 0=Deal armor damage to minion, 1=Give friendly +5/+5, 2=Gain 8 armor"""
    opp = _get_opponent(state, player)
    if idx == 0:
        if opp.board:
            target = max(opp.board, key=lambda m: m.health)
            target.take_damage(player.hero.armor)
    elif idx == 1:
        if player.board:
            target = max(player.board, key=lambda m: m.attack)
            if target is not minion:
                target.attack += 5
                target.health += 5
                target.max_health += 5
    elif idx == 2:
        player.hero.armor += 8


def _titan_norgannon(engine, state, player, minion, idx):
    """TTN_075 Norgannon (Mage): 0=Deal 4 randomly to enemies, 1=Add 2 free spells, 2=Copy opponent minion"""
    opp = _get_opponent(state, player)
    if idx == 0:
        targets = list(opp.board) + [opp.hero]
        for _ in range(4):
            if targets:
                random.choice(targets).take_damage(1)
    elif idx == 1:
        from src.simulator.game_state import HAND_LIMIT
        for _ in range(2):
            if len(player.hand) < HAND_LIMIT:
                spells = [c for c in engine.card_db.values() if c.get("card_type") == "SPELL"
                          and c.get("hero_class") in ("MAGE", "NEUTRAL")]
                if spells:
                    pick = random.choice(spells)
                    cid = pick["card_id"]
                    player.hand.append(cid)
                    engine.card_db[cid] = dict(engine.card_db.get(cid, pick))
                    engine.card_db[cid]["mana_cost"] = 0
    elif idx == 2:
        from src.simulator.game_state import HAND_LIMIT
        if opp.board and len(player.hand) < HAND_LIMIT:
            pick = random.choice(opp.board)
            player.hand.append(pick.card_id)


def _titan_yogg(engine, state, player, minion, idx):
    """YOG_516 Yogg-Saron (Neutral): 0=Steal minion with <=5 atk, 1=Fill board with random minions, 2=Deal 4 to all minions"""
    opp = _get_opponent(state, player)
    from src.simulator.game_state import BOARD_LIMIT
    if idx == 0:
        targets = [m for m in opp.board if m.attack <= 5]
        if targets and len(player.board) < BOARD_LIMIT:
            stolen = random.choice(targets)
            opp.board.remove(stolen)
            player.board.append(stolen)
    elif idx == 1:
        while len(player.board) < BOARD_LIMIT:
            pick = _random_minion_from_db(engine)
            if pick:
                _summon_token(player, pick.get("name", "Minion"), pick.get("attack", 1), pick.get("health", 1))
            else:
                break
    elif idx == 2:
        all_minions = list(player.board) + list(opp.board)
        for m in all_minions:
            if m is not minion:
                m.take_damage(4)


def _titan_amitus(engine, state, player, minion, idx):
    """TTN_858 Amitus (Paladin): 0=Deal 4 to minion, 1=Summon 2x 2/2 divine shield, 2=Give others divine shield"""
    opp = _get_opponent(state, player)
    if idx == 0:
        if opp.board:
            max(opp.board, key=lambda m: m.health).take_damage(4)
    elif idx == 1:
        _summon_token(player, "Recruit", 2, 2, divine_shield=True)
        _summon_token(player, "Recruit", 2, 2, divine_shield=True)
    elif idx == 2:
        for m in player.board:
            if m is not minion:
                m.divine_shield = True


def _titan_amanthul(engine, state, player, minion, idx):
    """TTN_429 Aman'Thul (Priest): 0=Remove enemy minion, 1=Discover from deck (draw 1), 2=Shuffle enemy minion into your deck"""
    opp = _get_opponent(state, player)
    if idx == 0:
        if opp.board:
            target = max(opp.board, key=lambda m: m.attack + m.health)
            opp.board.remove(target)
    elif idx == 1:
        player.draw_card()
    elif idx == 2:
        if opp.board:
            target = random.choice(opp.board)
            opp.board.remove(target)
            player.deck.append(target.card_id)


def _titan_v07tron(engine, state, player, minion, idx):
    """TTN_721 V-07-TR-0N (Rogue): 0=Deal 2 repeating, 1=Give +2 atk + windfury, 2=Gain +2/+2 + stealth"""
    opp = _get_opponent(state, player)
    if idx == 0:
        for m in list(opp.board):
            m.take_damage(2)
            if m.is_dead:
                continue
            else:
                break
    elif idx == 1:
        targets = [m for m in player.board if m is not minion]
        if targets:
            t = max(targets, key=lambda m: m.attack)
            t.attack += 2
            t.windfury = True
    elif idx == 2:
        minion.attack += 2
        minion.health += 2
        minion.max_health += 2
        minion.stealth = True


def _titan_golganneth(engine, state, player, minion, idx):
    """TTN_800 Golganneth (Shaman): 0=Give minions +2 atk, 1=Deal 6 + freeze random enemy, 2=Summon 2x 3/3 rush elementals"""
    opp = _get_opponent(state, player)
    if idx == 0:
        for m in player.board:
            if m is not minion:
                m.attack += 2
    elif idx == 1:
        if opp.board:
            t = random.choice(opp.board)
            t.take_damage(6)
            t.frozen = True
    elif idx == 2:
        _summon_token(player, "Elemental", 3, 3, rush=True)
        _summon_token(player, "Elemental", 3, 3, rush=True)


def _titan_sargeras(engine, state, player, minion, idx):
    """TTN_960 Sargeras (Warlock): 0=Draw 2, 1=Deal 3 to random enemy, 2=Destroy 3 random enemy minions"""
    opp = _get_opponent(state, player)
    if idx == 0:
        _draw_cards(player, 2)
    elif idx == 1:
        targets = list(opp.board) + [opp.hero]
        if targets:
            random.choice(targets).take_damage(3)
    elif idx == 2:
        for _ in range(3):
            if opp.board:
                target = random.choice(opp.board)
                target.health = 0


def _titan_khazgoroth(engine, state, player, minion, idx):
    """TTN_415 Khaz'goroth (Warrior): 0=Give +3/+3, 1=Equip 5/2 weapon, 2=Summon 4/6 taunt"""
    if idx == 0:
        targets = [m for m in player.board if m is not minion]
        if targets:
            t = max(targets, key=lambda m: m.attack)
            t.attack += 3
            t.health += 3
            t.max_health += 3
    elif idx == 1:
        from src.simulator.game_state import WeaponState
        player.hero.weapon = WeaponState("khaz_weapon", "Khaz'goroth's Hammer", 5, 2)
    elif idx == 2:
        _summon_token(player, "Stone Idol", 4, 6, taunt=True)


TITAN_HANDLERS = {
    "TTN_737": _titan_primus,
    "TTN_862": _titan_argus,
    "TTN_903": _titan_eonar,
    "TTN_092": _titan_aggramar,
    "TTN_075": _titan_norgannon,
    "YOG_516": _titan_yogg,
    "TTN_858": _titan_amitus,
    "TTN_429": _titan_amanthul,
    "TTN_721": _titan_v07tron,
    "TTN_800": _titan_golganneth,
    "TTN_960": _titan_sargeras,
    "TTN_415": _titan_khazgoroth,
}
