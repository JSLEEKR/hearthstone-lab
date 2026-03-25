from __future__ import annotations
import re
from dataclasses import dataclass, field


@dataclass
class SpellEffect:
    effect_type: str  # "damage", "aoe_damage", "heal", "draw", "buff", "destroy", "summon", "armor", "freeze_all"
    value: int = 0
    value2: int = 0  # for buff: attack bonus, value = health bonus
    target: str = "auto"  # "enemy_hero", "enemy_minion", "all_enemy_minions", "all_minions", "friendly_minion", "self_hero", "random_enemy"


def parse_spell_effects(text: str) -> list[SpellEffect]:
    """Parse Korean card text into structured spell effects."""
    if not text:
        return []

    effects = []
    # Clean text
    text = re.sub(r'<[^>]+>', '', text)  # strip HTML
    text = re.sub(r'\$(\d+)', r'\1', text)  # $N -> N
    text = re.sub(r'#(\d+)', r'\1', text)  # #N -> N
    text = text.replace('[x]', '')

    # AOE damage to ALL minions: "모든 하수인에게 피해를 N 줍니다"
    m = re.search(r'모든\s*하수인에게\s*피해를\s*(\d+)\s*줍니다', text)
    if m:
        effects.append(SpellEffect("aoe_damage", int(m.group(1)), target="all_minions"))
        return effects

    # AOE damage to enemy minions: "모든 적 하수인에게 피해를 N 줍니다"
    m = re.search(r'모든\s*적\s*하수인에게\s*피해를\s*(\d+)\s*줍니다', text)
    if m:
        effects.append(SpellEffect("aoe_damage", int(m.group(1)), target="all_enemy_minions"))
        return effects

    # Damage to enemy hero: "적 영웅에게 피해를 N 줍니다"
    m = re.search(r'적\s*영웅에게\s*피해를\s*(\d+)\s*줍니다', text)
    if m:
        effects.append(SpellEffect("damage", int(m.group(1)), target="enemy_hero"))
        return effects

    # Damage to a minion: "하수인 하나에게 피해를 N 줍니다"
    m = re.search(r'하수인\s*하나에게\s*피해를\s*(\d+)\s*줍니다', text)
    if m:
        effects.append(SpellEffect("damage", int(m.group(1)), target="enemy_minion"))
        return effects

    # Generic damage (single target): "피해를 N 줍니다"
    m = re.search(r'피해를\s*(\d+)\s*줍니다', text)
    if m and '모든' not in text:
        effects.append(SpellEffect("damage", int(m.group(1)), target="auto"))
        return effects

    # Heal: "체력을 N 회복합니다"
    m = re.search(r'체력을\s*(\d+)\s*회복', text)
    if m:
        effects.append(SpellEffect("heal", int(m.group(1)), target="auto"))
        return effects

    # Draw: "카드를 N장 뽑습니다" or "카드 N장을 뽑습니다"
    m = re.search(r'카드(?:를)?\s*(\d+)장', text)
    if m:
        effects.append(SpellEffect("draw", int(m.group(1))))
        return effects

    # Draw 1: "카드를 뽑습니다"
    if '카드를 뽑습니다' in text or '카드 한 장' in text:
        effects.append(SpellEffect("draw", 1))
        return effects

    # Buff: "+N/+N" or "+N 공격력"
    m = re.search(r'\+(\d+)/\+(\d+)', text)
    if m:
        effects.append(SpellEffect("buff", int(m.group(1)), int(m.group(2)), target="friendly_minion"))
        return effects

    # Armor: "방어도를 N 얻습니다"
    m = re.search(r'방어도를?\s*(\d+)\s*얻', text)
    if m:
        effects.append(SpellEffect("armor", int(m.group(1)), target="self_hero"))
        return effects

    # Destroy: "하수인 하나를 파괴합니다" or "파괴합니다"
    if '파괴합니다' in text and '하수인' in text:
        effects.append(SpellEffect("destroy", target="enemy_minion"))
        return effects

    # Freeze all: "모든 적 하수인을 빙결시킵니다"
    if '빙결' in text and '모든' in text:
        effects.append(SpellEffect("freeze_all", target="all_enemy_minions"))
        return effects

    # Silence: "하수인 하나를 침묵시킵니다" or "침묵"
    if '침묵' in text and '하수인' in text:
        effects.append(SpellEffect("silence", target="enemy_minion"))
        return effects

    # Summon: "N/N 하수인을 소환합니다" or "소환합니다"
    m = re.search(r'(\d+)/(\d+)\s*.*소환', text)
    if m:
        effects.append(SpellEffect("summon", int(m.group(1)), int(m.group(2))))
        return effects

    return effects


def parse_battlecry_effects(text: str) -> list[SpellEffect]:
    """Parse battlecry portion of text. Similar patterns but from minion cards."""
    if not text:
        return []
    # Look for text after "전투의 함성:" or whole text if it's clearly an effect
    bc_match = re.search(r'전투의 함성[:\s]+(.*?)(?:\.|$)', text, re.DOTALL)
    if bc_match:
        return parse_spell_effects(bc_match.group(1))
    return []


def parse_deathrattle_effects(text: str) -> list[SpellEffect]:
    """Parse deathrattle portion of text."""
    if not text:
        return []
    dr_match = re.search(r'죽음의 메아리[:\s]+(.*?)(?:\.|$)', text, re.DOTALL)
    if dr_match:
        return parse_spell_effects(dr_match.group(1))
    return []


def parse_combo_effects(text: str) -> list[SpellEffect]:
    """Parse combo portion of text (연계:)."""
    if not text:
        return []
    # Clean HTML tags first
    clean = re.sub(r'<[^>]+>', '', text)
    combo_match = re.search(r'연계[:\s]+(.*?)(?:\.|$)', clean, re.DOTALL)
    if combo_match:
        return parse_spell_effects(combo_match.group(1))
    return []


def parse_frenzy_effects(text: str) -> list[SpellEffect]:
    """Parse frenzy portion of text (광란:)."""
    if not text:
        return []
    clean = re.sub(r'<[^>]+>', '', text)
    m = re.search(r'광란[:\s]+(.*?)(?:\.|$)', clean, re.DOTALL)
    if m:
        return parse_spell_effects(m.group(1))
    return []


def parse_spellburst_effects(text: str) -> list[SpellEffect]:
    """Parse spellburst portion of text (주문폭발:)."""
    if not text:
        return []
    clean = re.sub(r'<[^>]+>', '', text)
    m = re.search(r'주문폭발[:\s]+(.*?)(?:\.|$)', clean, re.DOTALL)
    if m:
        return parse_spell_effects(m.group(1))
    return []


def parse_outcast_effects(text: str) -> list[SpellEffect]:
    """Parse outcast portion of text (추방자:)."""
    if not text:
        return []
    clean = re.sub(r'<[^>]+>', '', text)
    m = re.search(r'추방자[:\s]+(.*?)(?:\.|$)', clean, re.DOTALL)
    if m:
        return parse_spell_effects(m.group(1))
    return []


def parse_honorable_kill_effects(text: str) -> list[SpellEffect]:
    """Parse honorable kill portion of text (명예로운 처치:)."""
    if not text:
        return []
    clean = re.sub(r'<[^>]+>', '', text)
    m = re.search(r'명예로운 처치[:\s]+(.*?)(?:\.|$)', clean, re.DOTALL)
    if m:
        return parse_spell_effects(m.group(1))
    return []


def parse_inspire_effects(text: str) -> list[SpellEffect]:
    """Parse inspire portion of text (감화:)."""
    if not text:
        return []
    clean = re.sub(r'<[^>]+>', '', text)
    m = re.search(r'감화[:\s]+(.*?)(?:\.|$)', clean, re.DOTALL)
    if m:
        return parse_spell_effects(m.group(1))
    return []


def parse_manathirst_effects(text: str) -> tuple[int, list[SpellEffect]]:
    """Parse manathirst portion of text (마나 갈증 (N):). Returns (threshold, effects)."""
    if not text:
        return (0, [])
    clean = re.sub(r'<[^>]+>', '', text)
    m = re.search(r'마나 갈증\s*\((\d+)\)[:\s]+(.*?)(?:\.|$)', clean, re.DOTALL)
    if m:
        threshold = int(m.group(1))
        return (threshold, parse_spell_effects(m.group(2)))
    return (0, [])


def parse_overkill_effects(text: str) -> list[SpellEffect]:
    """Parse overkill portion of text (과잉살상:)."""
    if not text:
        return []
    clean = re.sub(r'<[^>]+>', '', text)
    m = re.search(r'과잉살상[:\s]+(.*?)(?:\.|$)', clean, re.DOTALL)
    if m:
        return parse_spell_effects(m.group(1))
    return []


def parse_overheal_effects(text: str) -> list[SpellEffect]:
    """Parse overheal portion of text (과치유:)."""
    if not text:
        return []
    clean = re.sub(r'<[^>]+>', '', text)
    m = re.search(r'과치유[:\s]+(.*?)(?:\.|$)', clean, re.DOTALL)
    if m:
        return parse_spell_effects(m.group(1))
    return []


def parse_infuse_threshold(text: str) -> int:
    """Parse infuse threshold from text (주입 (N) or just 주입:). Returns N or 1 as default."""
    if not text:
        return 0
    clean = re.sub(r'<[^>]+>', '', text)
    m = re.search(r'주입\s*\((\d+)\)', clean)
    if m:
        return int(m.group(1))
    if '주입' in clean:
        return 1
    return 0


def parse_infuse_effects(text: str) -> list[SpellEffect]:
    """Parse infuse bonus effects from text (주입:)."""
    if not text:
        return []
    clean = re.sub(r'<[^>]+>', '', text)
    # Try "주입 (N):" pattern first
    m = re.search(r'주입\s*(?:\(\d+\))?[:\s]+(.*?)(?:\.|$)', clean, re.DOTALL)
    if m:
        return parse_spell_effects(m.group(1))
    return []


def parse_choose_one_effects(text: str) -> list[SpellEffect]:
    """Parse choose-one text (선택 -). Returns effects of the first option."""
    if not text:
        return []
    clean = re.sub(r'<[^>]+>', '', text)
    # Pattern: "선택 - A 또는 B" or "선택: A; B"
    m = re.search(r'선택\s*[-:]\s*(.*?)(?:또는|;)', clean, re.DOTALL)
    if m:
        return parse_spell_effects(m.group(1).strip())
    # Fallback: just get text after "선택 -"
    m = re.search(r'선택\s*[-:]\s*(.*?)(?:\.|$)', clean, re.DOTALL)
    if m:
        return parse_spell_effects(m.group(1).strip())
    return []


def parse_quickdraw_effects(text: str) -> list[SpellEffect]:
    """Parse quickdraw bonus effects (속사:)."""
    if not text:
        return []
    clean = re.sub(r'<[^>]+>', '', text)
    m = re.search(r'속사[:\s]+(.*?)(?:\.|$)', clean, re.DOTALL)
    if m:
        return parse_spell_effects(m.group(1))
    return []
