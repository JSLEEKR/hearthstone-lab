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
    """VAC_437 Buttons: Draw a spell from each spell school in your deck. The real
    effect draws one spell per distinct school; our implementation draws 3 cards
    because the simulator does not track spell school filtering on deck contents."""
    _draw_cards(player, 3)


def _exarch_maladaar(engine, state, player, minion):
    """GDB_470 Exarch Maladaar: Next card costs Corpses instead of mana."""
    if player.hand:
        card_id = player.hand[0]
        cd = engine.card_db.get(card_id, {})
        if cd:
            original_cost = cd.get("mana_cost", 0)
            cd["mana_cost"] = 0
            player.corpses -= min(player.corpses, original_cost)


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
    """CORE_BT_187 Kayn Sunfury: Aura: adds IGNORE_TAUNT to all friendly minions.
    While Kayn is on board, friendly characters' attacks bypass enemy taunt minions."""
    minion.charge = True
    for m in player.board:
        if "IGNORE_TAUNT" not in m.mechanics:
            m.mechanics.append("IGNORE_TAUNT")


def _xortoth(engine, state, player, minion):
    """GDB_118 Xor'toth: If you completed the Star requirement, deal 5 damage to all
    enemies. The star mechanic requires hand/play tracking we do not have, so we
    always deal 5 damage to capture the card's intended late-game value."""
    _deal_damage_to_all_enemies(state, player, 5)


def _aranna_thrill_seeker(engine, state, player, minion):
    """VAC_501 Aranna Thrill Seeker: Ongoing aura that redirects damage dealt to your
    hero to a random enemy instead. The real effect lasts as long as Aranna is alive;
    our implementation grants 5 armor (representing 1-2 turns of damage mitigation)
    and deals 2 damage to a random enemy (representing redirected damage value)."""
    player.hero.armor += 5
    opp = _get_opponent(state, player)
    targets = list(opp.board) + [opp.hero]
    if targets:
        random.choice(targets).take_damage(2)


def _entomologist_toru(engine, state, player, minion):
    """TLC_841 Entomologist Toru: Put minions in hand into 0/1 Jars costing 1 mana.
    When a Jar is played, the minion inside comes out. Our implementation sets all
    MINION cards in hand to cost 1 because in simulation the Jar is played immediately
    and releases its minion, making cost-1 functionally equivalent."""
    for card_id in player.hand:
        card = engine.card_db.get(card_id, {})
        if card and card.get("card_type") == "MINION":
            card["mana_cost"] = 1


# ---------------------------------------------------------------------------
# DRUID
# ---------------------------------------------------------------------------

def _exarch_othaar(engine, state, player, minion):
    """GDB_856 Exarch Othaar: If building a Starship, get 3 Arcane spells with cost
    reduced by 2. Our implementation generates 3 random spells (no Arcane filter
    since spell school data is not available in simulation) with cost reduced by 2."""
    from src.simulator.game_state import HAND_LIMIT
    spells = [c for c in engine.card_db.values()
              if c.get("card_type") == "SPELL"
              and not c.get("card_id", "").startswith("token_")]
    for _ in range(3):
        if len(player.hand) >= HAND_LIMIT or not spells:
            break
        pick = random.choice(spells)
        cid = pick.get("card_id", "")
        player.hand.append(cid)
        # Reduce cost by 2 in card_db
        card = engine.card_db.get(cid, {})
        if card:
            card["mana_cost"] = max(0, card.get("mana_cost", 0) - 2)


def _fandral_staghelm(engine, state, player, minion):
    """CORE_OG_044 Fandral Staghelm: Aura that makes Choose One cards activate both
    options instead of picking one. The card's value is its 3/6 body plus the aura;
    we add the CHOOSE_ONE_BOTH mechanic tag but cannot generically implement the
    aura effect on future Choose One plays."""
    if "CHOOSE_ONE_BOTH" not in minion.mechanics:
        minion.mechanics.append("CHOOSE_ONE_BOTH")


def _ulfar(engine, state, player, minion):
    """CORE_CATA_006 Ulfar: Give other friendly minions 'Deathrattle: Summon a minion
    with stats equal to that minion's mana cost'. Adds DEATHRATTLE mechanic to each
    other friendly minion and registers deathrattle text that summons an N/N token
    where N is the minion's mana cost."""
    for m in player.board:
        if m is not minion:
            if "DEATHRATTLE" not in m.mechanics:
                m.mechanics.append("DEATHRATTLE")
            cost = m.mana_cost
            db_entry = dict(engine.card_db.get(m.card_id, {}))
            db_entry["text"] = f"죽음의 메아리: {cost}/{cost} 하수인을 소환합니다"
            engine.card_db[m.card_id] = db_entry


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
    """TOY_357 King Plush: Return ALL minions with less attack than this to their
    owner's deck. Affects both friendly and enemy boards."""
    opp = _get_opponent(state, player)
    # Return enemy minions with less attack
    enemy_returned = [m for m in opp.board if m.attack < minion.attack]
    for m in enemy_returned:
        opp.board.remove(m)
        opp.deck.append(m.card_id)
    # Return friendly minions with less attack (excluding self)
    friendly_returned = [m for m in player.board if m is not minion and m.attack < minion.attack]
    for m in friendly_returned:
        player.board.remove(m)
        player.deck.append(m.card_id)
    random.shuffle(opp.deck)
    random.shuffle(player.deck)


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
    """WORK_063 Portalmancer Skyla: Swap the mana costs of the lowest and highest cost
    spells in hand."""
    spells = []
    for card_id in player.hand:
        card = engine.card_db.get(card_id, {})
        if card.get("card_type") == "SPELL":
            spells.append((card_id, card))
    if len(spells) >= 2:
        lowest = min(spells, key=lambda x: x[1].get("mana_cost", 0))
        highest = max(spells, key=lambda x: x[1].get("mana_cost", 0))
        low_cost = lowest[1].get("mana_cost", 0)
        high_cost = highest[1].get("mana_cost", 0)
        lowest[1]["mana_cost"] = high_cost
        highest[1]["mana_cost"] = low_cost


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
    """DINO_410 Egg of Khelos: Deathrattle chain that hatches through multiple egg
    stages before becoming a full minion. Each stage summons a slightly larger egg.
    Our implementation registers one deathrattle stage (summon a 0/5 egg) because
    the full multi-stage chain is too complex to model in simulation."""
    if "DEATHRATTLE" not in minion.mechanics:
        minion.mechanics.append("DEATHRATTLE")
    db_entry = dict(engine.card_db.get(minion.card_id, {}))
    db_entry["text"] = "죽음의 메아리: 0/5 하수인을 소환합니다"
    engine.card_db[minion.card_id] = db_entry


def _gorgonzormu(engine, state, player, minion):
    """VAC_955 Gorgonzormu: Get a Cheese that summons three 1-cost minions. Adds a
    2-cost Cheese spell token to hand that summons 3 tokens when played."""
    from src.simulator.game_state import HAND_LIMIT
    if "token_Cheese" not in engine.card_db:
        engine.card_db["token_Cheese"] = {
            "card_id": "token_Cheese", "name": "Cheese", "card_type": "SPELL",
            "mana_cost": 2, "text": "1/1 하수인을 3개 소환합니다.",
            "mechanics": [],
        }
    if len(player.hand) < HAND_LIMIT:
        player.hand.append("token_Cheese")


def _black_knight(engine, state, player, minion):
    """CORE_EX1_002 Black Knight: destroy an enemy taunt minion."""
    opp = _get_opponent(state, player)
    taunts = [m for m in opp.board if m.taunt]
    if taunts:
        target = random.choice(taunts)
        target.health = 0


def _tindral_sageswift(engine, state, player, minion):
    """FIR_958 Tindral Sageswift: Deathrattle that deals 1 damage to all enemies on
    your turn, or 4 on the opponent's turn. We register the base 1 damage version
    since the engine does not distinguish whose turn a deathrattle triggers on."""
    if "DEATHRATTLE" not in minion.mechanics:
        minion.mechanics.append("DEATHRATTLE")
    db_entry = dict(engine.card_db.get(minion.card_id, {}))
    db_entry["text"] = "죽음의 메아리: 모든 적에게 피해를 1 줍니다"
    engine.card_db[minion.card_id] = db_entry


def _elise_the_navigator(engine, state, player, minion):
    """TLC_100 Elise the Navigator: If your starting deck contained 10 different mana
    costs, craft a Location. Locations are persistent board effects with durability;
    our implementation summons a 0/5 token with taunt to represent the board presence
    and durability of a Location since Location mechanics are not modeled."""
    _summon_token(player, "Map Location", 0, 5, taunt=True)


def _torga(engine, state, player, minion):
    """TLC_102 Torga: Dredge 3 cards from the bottom of your deck, then draw them.
    The real effect lets you pick from bottom-of-deck cards; our implementation
    draws 2 cards as the functional equivalent since dredge selection is not modeled."""
    _draw_cards(player, 2)


def _splendiferous_whizbang(engine, state, player, minion):
    """TOY_700 Splendiferous Whizbang: stat body only."""
    pass


def _the_curator(engine, state, player, minion):
    """CORE_KAR_061 The Curator: Draw a Beast, Dragon, and Murloc from your deck.
    Searches deck for the first card of each race and draws them specifically."""
    target_races = ["BEAST", "DRAGON", "MURLOC"]
    for race in target_races:
        for i, card_id in enumerate(player.deck):
            card = engine.card_db.get(card_id, {})
            if race in card.get("races", []):
                player.deck.pop(i)
                from src.simulator.game_state import HAND_LIMIT
                if len(player.hand) < HAND_LIMIT:
                    player.hand.append(card_id)
                break


def _taelan_fordring(engine, state, player, minion):
    """CS3_024 Taelan Fordring: Taunt, Divine Shield. Deathrattle: Draw the highest-cost
    minion from your deck. On play, sets up the deathrattle mechanic and moves the
    highest-cost minion to the top of the deck so the deathrattle draw gets it."""
    minion.taunt = True
    minion.divine_shield = True
    if "DEATHRATTLE" not in minion.mechanics:
        minion.mechanics.append("DEATHRATTLE")
    # Register deathrattle text for engine parsing
    db_entry = dict(engine.card_db.get(minion.card_id, {}))
    db_entry["text"] = "도발, 천상의 보호막, 죽음의 메아리: 카드를 1장 뽑습니다"
    engine.card_db[minion.card_id] = db_entry
    # Move highest cost minion to top of deck so deathrattle draw gets it
    best_idx = -1
    best_cost = -1
    for i, card_id in enumerate(player.deck):
        card = engine.card_db.get(card_id, {})
        if card.get("card_type") == "MINION" and card.get("mana_cost", 0) > best_cost:
            best_cost = card.get("mana_cost", 0)
            best_idx = i
    if best_idx > 0:
        player.deck.insert(0, player.deck.pop(best_idx))


def _vyranoth(engine, state, player, minion):
    """CATA_213 Vyranoth: If your deck started with 100 mana worth of cards, give all
    minions in your deck +2/+2. The 100-mana condition is checked via turn >= 10 as
    a proxy (late game implies a high-cost deck). Buffs card_db entries for cards
    remaining in the player's deck."""
    if state.turn >= 10:
        for card_id in player.deck:
            card = engine.card_db.get(card_id, {})
            if card.get("card_type") == "MINION":
                card["attack"] = card.get("attack", 0) + 2
                card["health"] = card.get("health", 0) + 2


def _ultraxion(engine, state, player, minion):
    """CATA_497 Ultraxion: Herald/Foretell mechanic that brings Deathwing closer.
    Increments the player's herald_count and reduces any Deathwing card in the
    card_db by 3 mana, representing the Foretell discount."""
    player.herald_count += 1
    for cid, card in engine.card_db.items():
        if "deathwing" in card.get("name", "").lower() or "GAME_005" in cid:
            card["mana_cost"] = max(0, card.get("mana_cost", 0) - 3)
            break


def _chromie(engine, state, player, minion):
    """TIME_103 Chromie: Deathrattle: Draw copies of all cards played this game."""
    n = min(len(player.played_cards_this_game), 5)  # cap at 5
    if "DEATHRATTLE" not in minion.mechanics:
        minion.mechanics.append("DEATHRATTLE")
    db_entry = dict(engine.card_db.get(minion.card_id, {}))
    db_entry["text"] = f"죽음의 메아리: 카드를 {n}장 뽑습니다"
    engine.card_db[minion.card_id] = db_entry


def _warmaster_blackhorn(engine, state, player, minion):
    """CATA_720 Warmaster Blackhorn: destroy all cards costing 2 or less in both decks."""
    opp = _get_opponent(state, player)
    player.deck = [c for c in player.deck
                   if engine.card_db.get(c, {}).get("mana_cost", 0) > 2]
    opp.deck = [c for c in opp.deck
                if engine.card_db.get(c, {}).get("mana_cost", 0) > 2]


def _the_exodar(engine, state, player, minion):
    """GDB_120 The Exodar: Launch a Starship if you have enough parts (3+), otherwise
    summon a smaller vessel. If the player has collected >= 3 starship pieces, summons
    an 8/8 with rush representing the assembled starship; otherwise summons a 5/5."""
    if player.starship_parts >= 3:
        _summon_token(player, "Starship Exodar", 8, 8, rush=True)
    else:
        _summon_token(player, "Draenei", 5, 5)


def _velen(engine, state, player, minion):
    """GDB_131 Velen: Taunt. Deathrattle: Trigger the Battlecry and Deathrattle of every
    other Draenei you played this game. The real effect replays all Draenei effects;
    our implementation registers a deathrattle dealing 3 damage to all enemies as a
    reasonable aggregate representation of multiple deathrattle triggers."""
    if "DEATHRATTLE" not in minion.mechanics:
        minion.mechanics.append("DEATHRATTLE")
    db_entry = dict(engine.card_db.get(minion.card_id, {}))
    db_entry["text"] = "도발, 죽음의 메아리: 모든 적에게 피해를 3 줍니다"
    engine.card_db[minion.card_id] = db_entry


def _endbringer_umbra(engine, state, player, minion):
    """TLC_106 Endbringer Umbra: Trigger 5 friendly deathrattles that died this game.
    The real effect replays past deathrattles; our implementation produces typical
    deathrattle value: 3 damage to all enemies, draw 1 card, and summon a 3/3 token."""
    opp = _get_opponent(state, player)
    # Deal 3 damage to all enemies
    opp.hero.take_damage(3)
    for m in list(opp.board):
        m.take_damage(3)
    # Draw 1
    _draw_cards(player, 1)
    # Summon a 3/3
    _summon_token(player, "Spirit", 3, 3)


def _mayor_noggenfogger(engine, state, player, minion):
    """CORE_CFM_670 Mayor Noggenfogger: All targets are chosen randomly. Adds FORGETFUL
    to ALL minions on both boards so any targeted action picks a random valid target."""
    opp = _get_opponent(state, player)
    for m in player.board:
        if "FORGETFUL" not in m.mechanics:
            m.mechanics.append("FORGETFUL")
    for m in opp.board:
        if "FORGETFUL" not in m.mechanics:
            m.mechanics.append("FORGETFUL")


def _avatar_of_hearthstone(engine, state, player, minion):
    """CORE_WON_145 Avatar of Hearthstone: Open a pack and PLAY all cards. A pack
    contains a mix of minions and spells; our implementation summons up to 3 random
    minions to the board and adds 2 random spells to hand."""
    from src.simulator.game_state import BOARD_LIMIT, HAND_LIMIT
    minion_cards = [c for c in engine.card_db.values()
                    if c.get("card_type") == "MINION"
                    and not c.get("card_id", "").startswith("token_")
                    and not c.get("card_id", "").endswith("_mini")]
    spell_cards = [c for c in engine.card_db.values()
                   if c.get("card_type") == "SPELL"
                   and not c.get("card_id", "").startswith("token_")]
    for _ in range(3):
        if len(player.board) >= BOARD_LIMIT or not minion_cards:
            break
        pick = random.choice(minion_cards)
        _summon_token(player, pick.get("name", "Minion"),
                      pick.get("attack", 1), pick.get("health", 1))
    for _ in range(2):
        if len(player.hand) >= HAND_LIMIT or not spell_cards:
            break
        pick = random.choice(spell_cards)
        player.hand.append(pick.get("card_id", ""))


def _endtime_murozond(engine, state, player, minion):
    """END_037 Endtime Murozond: Fill board with random dragons, full heal hero, but
    skip your next turn. Sets player mana to 0 on the following turn as the penalty
    for skipping (closest functional equivalent since true turn-skip is not supported)."""
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
    # Penalty: set overload equal to max_mana so next turn mana is 0
    player.overload = 10


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
    """EDR_258 Toreth: Has triple divine shield — when broken, it comes back twice more.
    The real effect reapplies divine_shield twice after it breaks; our implementation
    sets divine_shield and adds +6 health as extra survivability since we cannot hook
    into divine_shield-break events in the engine."""
    minion.divine_shield = True
    if "DIVINE_SHIELD" not in minion.mechanics:
        minion.mechanics.append("DIVINE_SHIELD")
    minion.health += 6
    minion.max_health += 6


def _toy_captain_tarim(engine, state, player, minion):
    """TOY_813 Toy Captain Tarim: Set ALL minions' stats to match this minion's
    attack and health. Affects both friendly and enemy boards."""
    opp = _get_opponent(state, player)
    for m in list(player.board) + list(opp.board):
        if m is not minion:
            m.attack = minion.attack
            m.health = minion.health
            m.max_health = minion.health


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
    """EDR_259 Ursol: Cast the highest cost spell in your hand, and repeat it at the
    end of your next 2 turns (3 total casts). Our implementation casts the spell once
    because recurring end-of-turn triggers require engine hooks we do not have."""
    from src.simulator.game_state import HAND_LIMIT
    best_spell = None
    best_cost = -1
    best_idx = -1
    for i, card_id in enumerate(player.hand):
        card = engine.card_db.get(card_id, {})
        if card.get("card_type") == "SPELL" and card.get("mana_cost", 0) > best_cost:
            best_cost = card.get("mana_cost", 0)
            best_spell = card
            best_idx = i
    if best_spell and best_idx >= 0:
        # Parse and apply the spell's effects
        from src.simulator.spell_parser import parse_spell_effects
        effects = parse_spell_effects(best_spell.get("text", ""))
        if effects:
            engine._apply_battlecry_effects(state, player, minion, effects)
        # Remove the spell from hand
        player.hand.pop(best_idx)


# ---------------------------------------------------------------------------
# PRIEST
# ---------------------------------------------------------------------------

def _chillin_voljin(engine, state, player, minion):
    """VAC_957 Chillin Vol'jin: Choose 2 minions, swap their stats. Swaps the highest
    stat enemy minion with the lowest stat friendly minion."""
    opp = _get_opponent(state, player)
    if opp.board and player.board:
        highest_enemy = max(opp.board, key=lambda m: m.attack + m.health)
        lowest_friendly = min(player.board, key=lambda m: m.attack + m.health)
        (highest_enemy.attack, lowest_friendly.attack) = (lowest_friendly.attack, highest_enemy.attack)
        (highest_enemy.health, lowest_friendly.health) = (lowest_friendly.health, highest_enemy.health)
        (highest_enemy.max_health, lowest_friendly.max_health) = (lowest_friendly.max_health, highest_enemy.max_health)


def _narain_soothfancy(engine, state, player, minion):
    """VAC_420 Narain Soothfancy: Get 2 Prophecy cards that transform into copies of
    whatever card you play next. The real effect copies your next played card twice;
    our implementation generates 2 random cards to hand since we cannot track future
    card plays to determine what the prophecies would become."""
    from src.simulator.game_state import HAND_LIMIT
    all_cards = [c for c in engine.card_db.values()
                 if not c.get("card_id", "").startswith("token_")
                 and not c.get("card_id", "").endswith("_mini")]
    if not all_cards:
        return
    for _ in range(2):
        if len(player.hand) >= HAND_LIMIT:
            break
        card = random.choice(all_cards)
        player.hand.append(card.get("card_id", ""))


def _timewinder_zarimi(engine, state, player, minion):
    """TOY_385 Zarimi: If 8 other Dragons played, take extra turn."""
    dragon_count = sum(1 for p in player.played_cards_this_game
                       if p.get("race") == "DRAGON")
    if dragon_count >= 8:
        _draw_cards(player, 3)
        for m in player.board:
            m.rush = True
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
    """EDR_464 Tyrande: Next 3 spells are cast twice."""
    player.next_spell_cast_twice_count = 3


# ---------------------------------------------------------------------------
# ROGUE
# ---------------------------------------------------------------------------

def _mirrex(engine, state, player, minion):
    """DINO_407 Mirrex: In hand, becomes a copy of the last opponent minion played.
    On play, copies a random enemy minion's card_id stats but keeps 3/4 body."""
    opp = _get_opponent(state, player)
    if opp.board:
        src = random.choice(opp.board)
        # Copy the card_id stats from the enemy minion but set to 3/4
        minion.card_id = src.card_id
        minion.name = src.name
        minion.attack = 3
        minion.health = 4
        minion.max_health = 4
        minion.mechanics = list(src.mechanics)


def _opu_the_unseen(engine, state, player, minion):
    """TLC_522 Opu the Unseen: Battlecry + Combo + Deathrattle: Fan of Knives. Deals 1
    damage to all enemy minions (not hero) and draws 1. If combo (cards played this turn),
    repeats the effect. Sets up deathrattle text for death trigger."""
    opp = _get_opponent(state, player)
    # Fan of Knives: 1 damage to all enemy MINIONS only
    for m in list(opp.board):
        m.take_damage(1)
    player.draw_card()
    # Combo: if another card was played this turn, do it again
    if player.cards_played_this_turn > 0:
        for m in list(opp.board):
            m.take_damage(1)
        player.draw_card()
    # Set up deathrattle for death trigger
    if "DEATHRATTLE" not in minion.mechanics:
        minion.mechanics.append("DEATHRATTLE")
    db_entry = dict(engine.card_db.get(minion.card_id, {}))
    db_entry["text"] = "죽음의 메아리: 모든 적 하수인에게 피해를 1 줍니다"
    engine.card_db[minion.card_id] = db_entry


# ---------------------------------------------------------------------------
# SHAMAN
# ---------------------------------------------------------------------------

def _bralma_searstone(engine, state, player, minion):
    """TLC_228 Bralma Searstone: Aura that makes your Elemental cards deal +1 damage.
    Implemented as spell power +1 since it is functionally equivalent for simulation
    purposes — both add +1 to outgoing damage from the controlling player."""
    if "SPELLPOWER" not in minion.mechanics:
        minion.mechanics.append("SPELLPOWER")


def _farseer_nobundo(engine, state, player, minion):
    """GDB_447 Farseer Nobundo: Deathrattle: Open a Galactic Lens. On play, sets up
    the deathrattle mechanic with parseable text for the engine to handle on death."""
    if "DEATHRATTLE" not in minion.mechanics:
        minion.mechanics.append("DEATHRATTLE")
    db_entry = dict(engine.card_db.get(minion.card_id, {}))
    db_entry["text"] = "죽음의 메아리: 카드를 1장 뽑습니다"
    engine.card_db[minion.card_id] = db_entry


def _kragwa(engine, state, player, minion):
    """CORE_TRL_345 Krag'wa: Return all spells cast last turn to hand."""
    from src.simulator.game_state import HAND_LIMIT
    for spell_id in player.spells_cast_last_turn:
        if len(player.hand) < HAND_LIMIT:
            player.hand.append(spell_id)


def _shudderblock(engine, state, player, minion):
    """TOY_501 Shudderblock: Next Battlecry triggers 3 times (can't damage enemy hero)."""
    player.next_battlecry_multiplier = 3


def _murmur(engine, state, player, minion):
    """GDB_448 Murmur: Battlecry minions cost 1 but die on play. Sets all minion cards
    in hand that have BATTLECRY mechanic to cost 1."""
    for card_id in player.hand:
        card = engine.card_db.get(card_id, {})
        if card.get("card_type") == "MINION" and "BATTLECRY" in card.get("mechanics", []):
            card["mana_cost"] = 1


# ---------------------------------------------------------------------------
# WARLOCK
# ---------------------------------------------------------------------------

def _razidir(engine, state, player, minion):
    """TLC_463 Razidir: Discard a random card. Dredge: from opponent instead.
    Discards a random card from the player's hand."""
    if player.hand:
        player.hand.pop(random.randrange(len(player.hand)))


def _game_master_nemsy(engine, state, player, minion):
    """TOY_524 Game Master Nemsy: Battlecry: Draw a Demon. Deathrattle: Swap places with
    that Demon. Searches deck for the first card with DEMON race and draws it specifically.
    Sets up deathrattle for the swap effect."""
    # Search deck for a demon and draw it specifically
    demon_idx = -1
    for i, card_id in enumerate(player.deck):
        card = engine.card_db.get(card_id, {})
        if card.get("card_type") == "MINION" and "DEMON" in card.get("races", []):
            demon_idx = i
            break
    if demon_idx >= 0:
        # Move demon to front of deck so draw_card gets it
        player.deck.insert(0, player.deck.pop(demon_idx))
    player.draw_card()
    if "DEATHRATTLE" not in minion.mechanics:
        minion.mechanics.append("DEATHRATTLE")


def _archimonde(engine, state, player, minion):
    """GDB_128 Archimonde: Summon all Demons played this game not in starting deck."""
    from src.simulator.game_state import MinionState, BOARD_LIMIT
    for played in player.played_cards_this_game:
        if len(player.board) >= BOARD_LIMIT:
            break
        if played.get("race") == "DEMON" or "DEMON" in str(played.get("mechanics", [])):
            card = engine.card_db.get(played["card_id"], {})
            if card.get("card_type") == "MINION":
                _summon_token(player, card.get("name", "Demon"),
                              card.get("attack", 3), card.get("health", 3))


def _party_planner_vona(engine, state, player, minion):
    """VAC_945 Vona: If you took 8 damage on your turn, summon Ouroboros."""
    hp_lost = player.hero_hp_at_turn_start - (player.hero.health + player.hero.armor)
    if hp_lost >= 8:
        _summon_token(player, "Ouroboros", 8, 8, rush=True)


def _agamaggan(engine, state, player, minion):
    """EDR_489 Agamaggan: Next card costs enemy HP instead of mana. Sets the highest cost
    card in hand to cost 0 and deals that original cost as damage to the enemy hero."""
    opp = _get_opponent(state, player)
    best_card = None
    best_cost = -1
    for card_id in player.hand:
        card = engine.card_db.get(card_id, {})
        if card and card.get("mana_cost", 0) > best_cost:
            best_cost = card.get("mana_cost", 0)
            best_card = card
    if best_card and best_cost > 0:
        best_card["mana_cost"] = 0
        opp.hero.take_damage(best_cost)


# ---------------------------------------------------------------------------
# TITAN BATTLECRY helpers (on-play effects, separate from titan ability handlers)
# ---------------------------------------------------------------------------

def _aggramar_battlecry(engine, state, player, minion):
    """TTN_092 Aggramar: On play, equip a 3/3 weapon."""
    from src.simulator.game_state import WeaponState
    player.hero.weapon = WeaponState(
        card_id="aggramar_weapon", name="Aggramar's Sword",
        attack=3, durability=3,
    )


def _sargeras_battlecry(engine, state, player, minion):
    """TTN_960 Sargeras: On play, open a portal that summons two 3/2 Imp tokens."""
    _summon_token(player, "Imp", 3, 2)
    _summon_token(player, "Imp", 3, 2)


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

    # TITAN BATTLECRIES (on-play effects separate from titan abilities)
    "TTN_092": _aggramar_battlecry,
    "TTN_960": _sargeras_battlecry,
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
