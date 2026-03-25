from __future__ import annotations
import re
from dataclasses import dataclass, field


@dataclass
class SpellEffect:
    effect_type: str  # "damage", "aoe_damage", "heal", "draw", "buff", "destroy", "summon", "armor", "freeze_all", "grant_keyword", "cost_reduction", "set_cost", "random_summon", "random_generate", "discover", "transform", "resurrect", "shuffle_into_deck", "silence"
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

    # Grant keyword: "속공을 부여/얻습니다"
    keyword_map = {
        '속공': 'RUSH', '돌진': 'RUSH', '도발': 'TAUNT', '질풍': 'WINDFURY',
        '은신': 'STEALTH', '천상의 보호막': 'DIVINE_SHIELD',
        '생명력 흡수': 'LIFESTEAL', '독성': 'POISONOUS', '환생': 'REBORN',
    }
    for kr_name, en_name in keyword_map.items():
        if kr_name in text and ('부여' in text or '얻습니다' in text):
            effects.append(SpellEffect("grant_keyword", target=en_name))
            return effects

    # Cost reduction: "비용이 (N) 감소"
    m = re.search(r'비용이?\s*\((\d+)\)\s*감소', text)
    if m:
        effects.append(SpellEffect("cost_reduction", int(m.group(1)), target="hand"))
        return effects

    # Set cost: "비용이 (N)이 됩니다" or "비용은 (N)이 됩니다"
    m = re.search(r'비용(?:이|은|을)?\s*\(?(\d+)\)?\s*(?:이\s*)?됩니다', text)
    if m:
        effects.append(SpellEffect("set_cost", int(m.group(1)), target="hand"))
        return effects

    # Transform: "변신" or "변환"
    if '변신' in text or ('변환' in text and '하수인' in text):
        effects.append(SpellEffect("transform", target="enemy_minion"))
        return effects

    # Resurrect: "부활" or "되살"
    if '부활' in text or '되살' in text:
        m = re.search(r'(\d+)', text)
        count = int(m.group(1)) if m else 1
        effects.append(SpellEffect("resurrect", count, target="friendly_board"))
        return effects

    # Shuffle into deck: "섞어" or "섞습니다"
    if '섞' in text and '덱' in text:
        m = re.search(r'(\d+)', text)
        count = int(m.group(1)) if m else 1
        effects.append(SpellEffect("shuffle_into_deck", count, target="deck"))
        return effects

    # Double: "2배" or "두 배"
    if '2배' in text or '두 배' in text:
        if '능력치' in text or '공격력' in text:
            effects.append(SpellEffect("buff", 0, 0, target="double_stats"))
        else:
            effects.append(SpellEffect("draw", 1))  # simplified
        return effects

    # Replay/repeat: "반복" or "다시 시전"
    if '반복' in text or '다시 시전' in text:
        effects.append(SpellEffect("draw", 1))  # simplified as card advantage
        return effects

    # Immune: "면역"
    if '면역' in text and '하수인' not in text:
        effects.append(SpellEffect("grant_keyword", target="IMMUNE"))
        return effects

    # Board clear: "모든 하수인을 파괴" or "모두 처치"
    if ('모든' in text or '모두' in text) and ('파괴' in text or '처치' in text) and '하수인' in text:
        effects.append(SpellEffect("aoe_damage", 999, target="all_minions"))
        return effects

    # Add to hand: "가져옵니다" or "손으로"
    if '가져옵니다' in text or ('손으로' in text and ('추가' in text or '가져' in text)):
        m = re.search(r'(\d+)장', text)
        count = int(m.group(1)) if m else 1
        effects.append(SpellEffect("random_generate", count, target="hand"))
        return effects

    # Hero power change: "영웅 능력" + "교체"
    if '영웅 능력' in text and '교체' in text:
        effects.append(SpellEffect("draw", 1))  # simplified
        return effects

    # Saga: "설화" — multi-chapter card, simplified as draw
    if '설화' in text:
        effects.append(SpellEffect("draw", 1))
        return effects

    # Tourist: "관광객" — deckbuilding effect. But some cards have effects AFTER "관광객"
    if '관광객' in text:
        # Strip the tourist prefix and try to parse the rest
        rest = re.sub(r'.*관광객\s*', '', text).strip()
        if rest:
            rest_effects = parse_spell_effects(rest)
            if rest_effects:
                return rest_effects
        return effects  # return empty — handled as stat body

    # Corpse: "시체" — DK mechanic, simplified
    if '시체' in text and '소모' in text:
        effects.append(SpellEffect("buff", 2, 2, target="friendly_minion"))
        return effects

    # Random summon: "무작위 하수인을 소환" or "무작위 N코스트 하수인 소환"
    if '무작위' in text and '소환' in text:
        m = re.search(r'무작위\s*(\d+)코스트', text)
        cost = int(m.group(1)) if m else 0
        effects.append(SpellEffect("random_summon", cost, target="friendly_board"))
        return effects

    # Random generate: "무작위 X를 얻습니다"
    if '무작위' in text and '얻습니다' in text:
        effects.append(SpellEffect("random_generate", 1, target="hand"))
        return effects

    # Discover from text
    if '발견' in text:
        effects.append(SpellEffect("discover", target="hand"))
        return effects

    # Copy: "복사합니다"
    if '복사' in text:
        effects.append(SpellEffect("draw", 1))
        return effects

    # Attack buff only: "공격력을 +N" without health
    m = re.search(r'공격력을?\s*\+(\d+)', text)
    if m and '+' in text and '/' not in text:
        effects.append(SpellEffect("buff", int(m.group(1)), 0, target="friendly_minion"))
        return effects

    # AOE damage to all enemies (including hero): "모든 적에게 피해를 N"
    m = re.search(r'모든\s*적에게\s*피해를\s*(\d+)', text)
    if m and '하수인' not in text:
        effects.append(SpellEffect("aoe_damage", int(m.group(1)), target="all_enemy_minions"))
        return effects

    # AOE damage to ALL characters: "모든 캐릭터에게 피해를 N"
    m = re.search(r'모든\s*캐릭터에게\s*피해를\s*(\d+)', text)
    if m:
        effects.append(SpellEffect("aoe_damage", int(m.group(1)), target="all_minions"))
        return effects

    # AOE damage to ALL minions: "모든 하수인에게 피해를 N 줍니다"
    m = re.search(r'모든\s*하수인에게\s*피해를\s*(\d+)', text)
    if m:
        effects.append(SpellEffect("aoe_damage", int(m.group(1)), target="all_minions"))
        return effects

    # AOE damage to enemy minions: "모든 적 하수인에게 피해를 N 줍니다"
    m = re.search(r'모든\s*적\s*하수인에게\s*피해를\s*(\d+)', text)
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

    # Random split damage: "N의 피해를 무작위로 나누어 입힙니다"
    m = re.search(r'(\d+)의?\s*피해를\s*무작위로\s*나누어', text)
    if m:
        target = "all_enemy_minions" if '적' in text else "all_minions"
        effects.append(SpellEffect("aoe_damage", int(m.group(1)), target=target))
        return effects

    # Random multi-hit: "피해를 N씩 주는 화살 N개" or "피해를 N씩 줍니다"
    m = re.search(r'피해를\s*(\d+)씩', text)
    if m:
        effects.append(SpellEffect("aoe_damage", int(m.group(1)), target="all_minions"))
        return effects

    # Generic damage (single target): "피해를 N 줍니다" or "피해를 N 주고"
    m = re.search(r'피해를\s*(\d+)\s*(?:줍니다|주고|줌)', text)
    if m and '모든' not in text:
        effects.append(SpellEffect("damage", int(m.group(1)), target="auto"))
        # Check for secondary damage after "주고": "주고 다른 모든 적에게 피해를 N"
        m2 = re.search(r'주고.*모든.*적.*피해를\s*(\d+)', text)
        if m2:
            effects.append(SpellEffect("aoe_damage", int(m2.group(1)), target="all_enemy_minions"))
        return effects

    # Heal: "체력을 N 회복" or "생명력을 N 회복" or "회복시킵니다"
    m = re.search(r'(?:체력|생명력)을?\s*(\d+)\s*회복', text)
    if m:
        effects.append(SpellEffect("heal", int(m.group(1)), target="auto"))
        return effects

    # Draw: "카드를 N장 뽑습니다" or "카드 N장을 뽑습니다"
    m = re.search(r'카드(?:를)?\s*(\d+)장', text)
    if m:
        effects.append(SpellEffect("draw", int(m.group(1))))
        return effects

    # Draw 1: "카드를 뽑습니다" or "카드 한 장" or just "뽑습니다"
    if '카드를 뽑습니다' in text or '카드 한 장' in text or ('뽑습니다' in text and '카드' not in text):
        effects.append(SpellEffect("draw", 1))
        return effects

    # Buff: "+N/+N" or "+N 공격력"
    m = re.search(r'\+(\d+)/\+(\d+)', text)
    if m:
        effects.append(SpellEffect("buff", int(m.group(1)), int(m.group(2)), target="friendly_minion"))
        return effects

    # Armor: "방어도를 N 얻습니다" or "방어도를 +N 얻습니다"
    m = re.search(r'방어도를?\s*\+?(\d+)\s*얻', text)
    if m:
        effects.append(SpellEffect("armor", int(m.group(1)), target="self_hero"))
        return effects

    # Destroy: "하수인 하나를 파괴합니다" or "처치합니다"
    if ('파괴합니다' in text or '처치합니다' in text) and '하수인' in text:
        effects.append(SpellEffect("destroy", target="enemy_minion"))
        return effects

    # Freeze: "빙결" — freeze targets
    if '빙결' in text:
        if '모든' in text:
            effects.append(SpellEffect("freeze_all", target="all_enemy_minions"))
        else:
            effects.append(SpellEffect("freeze_all", target="enemy_minion"))
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

    # Generic summon without stats: "소환합니다"
    if '소환' in text:
        effects.append(SpellEffect("random_summon", 0, target="friendly_board"))
        return effects

    # Return to hand: "돌려보냅니다" or "되돌립니다"
    if '돌려' in text or '되돌' in text:
        effects.append(SpellEffect("damage", 0, target="enemy_minion"))  # bounce = pseudo-remove
        return effects

    # Mana crystal: "마나 수정" — gain/lose mana
    if '마나 수정' in text:
        m = re.search(r'(\d+)', text)
        val = int(m.group(1)) if m else 1
        if '얻' in text or '회복' in text:
            effects.append(SpellEffect("armor", val, target="self_hero"))
        elif '파괴' in text:
            effects.append(SpellEffect("destroy", target="enemy_minion"))
        elif '잠금 해제' in text or '해제' in text:
            effects.append(SpellEffect("buff", 0, 0, target="self"))
        else:
            effects.append(SpellEffect("buff", 0, 0, target="self"))
        return effects

    # Heal with "회복시킵니다" variant: "생명력을 N 회복시킵니다" or "N씩 회복"
    m = re.search(r'(\d+)\s*(?:씩\s*)?회복', text)
    if m and ('생명력' in text or '영웅' in text or '체력' in text):
        effects.append(SpellEffect("heal", int(m.group(1)), target="auto"))
        return effects

    # Health buff: "생명력을 +N 부여" or "생명력 +N"
    m = re.search(r'생명력을?\s*\+(\d+)', text)
    if m:
        effects.append(SpellEffect("buff", 0, int(m.group(1)), target="friendly_minion"))
        return effects

    # Set stats: "공격력과 생명력을 N으로" or "공격력과 생명력을 바꿉니다"
    if '공격력과 생명력을 바꿉니다' in text or '공격력과 생명력을 바꿔' in text:
        effects.append(SpellEffect("transform", target="all_minions"))
        return effects

    m = re.search(r'공격력과\s*생명력을?\s*(\d+)', text)
    if m:
        val = int(m.group(1))
        effects.append(SpellEffect("buff", val, val, target="all_minions"))
        return effects

    # Silence: "침묵" without "하수인"
    if '침묵' in text:
        effects.append(SpellEffect("silence", target="enemy_minion"))
        return effects

    # "비용이 (N)씩 감소" — cost reduction per something
    m = re.search(r'비용이?\s*\(?(\d+)\)?\s*(?:씩\s*)?감소', text)
    if m:
        effects.append(SpellEffect("cost_reduction", int(m.group(1)), target="hand"))
        return effects

    # "비용은 (N)이 됩니다" — set cost
    m = re.search(r'비용(?:은|이)\s*\(?(\d+)\)?\s*(?:이\s*)?됩니다', text)
    if m:
        effects.append(SpellEffect("set_cost", int(m.group(1)), target="hand"))
        return effects

    # "공격력을 N으로" — set attack
    m = re.search(r'공격력을?\s*(\d+)\s*(?:으|로)', text)
    if m:
        effects.append(SpellEffect("buff", int(m.group(1)), 0, target="enemy_minion"))
        return effects

    # "과부하" — overload (handled by engine as keyword)
    m = re.search(r'과부하[:\s]*\(?(\d+)\)?', text)
    if m:
        # Return a dummy effect so it counts as "parsed" — engine handles overload
        effects.append(SpellEffect("buff", 0, 0, target="self"))
        return effects

    # "아군 하수인" or "내 하수인" + buff without +N/+N pattern
    if ('아군' in text or '내 ' in text) and '하수인' in text and '얻습니다' in text:
        effects.append(SpellEffect("buff", 1, 1, target="friendly_minion"))
        return effects

    # --- EXTENDED PATTERNS ---

    # Equip weapon: "장착합니다" or "N/N ... 장착"
    m = re.search(r'(\d+)/(\d+)\s*[^.]*장착', text)
    if m:
        effects.append(SpellEffect("summon", int(m.group(1)), int(m.group(2)), target="weapon"))
        return effects
    if '장착' in text:
        effects.append(SpellEffect("summon", 2, 2, target="weapon"))
        return effects

    # Secret: "비밀:" — secret card
    if text.startswith('비밀:') or '비밀: ' in text:
        # Parse effect after "비밀:"
        secret_text = re.sub(r'^비밀:\s*', '', text)
        secret_effects = parse_spell_effects(secret_text)
        if secret_effects:
            return secret_effects
        # Default: grant keyword as proxy
        effects.append(SpellEffect("grant_keyword", target="DIVINE_SHIELD"))
        return effects

    # Proportional damage: "만큼 피해를" or "만큼의 피해"
    if '만큼' in text and '피해' in text:
        m = re.search(r'(\d+)', text)
        val = int(m.group(1)) if m else 3
        if '모든' in text:
            effects.append(SpellEffect("aoe_damage", val, target="all_enemy_minions"))
        else:
            effects.append(SpellEffect("damage", val, target="auto"))
        return effects

    # Proportional armor: "만큼 방어도"
    if '만큼' in text and '방어도' in text:
        effects.append(SpellEffect("armor", 3, target="self_hero"))
        return effects

    # Fill hand: "채웁니다" or "가득 채웁니다"
    if '채웁니다' in text and ('손' in text or '패' in text or '전장' in text):
        if '전장' in text:
            effects.append(SpellEffect("random_summon", 0, target="friendly_board"))
        else:
            effects.append(SpellEffect("random_generate", 3, target="hand"))
        return effects

    # Trigger ability: "능력을 발동" or "N번 발동"
    if '발동' in text and ('능력' in text or '번' in text):
        effects.append(SpellEffect("buff", 1, 1, target="friendly_minion"))
        return effects

    # Select/target: "선택합니다" (choose a target)
    if '선택합니다' in text:
        if '피해' in text:
            m = re.search(r'(\d+)', text)
            val = int(m.group(1)) if m else 3
            effects.append(SpellEffect("damage", val, target="auto"))
        elif '처치' in text or '파괴' in text:
            effects.append(SpellEffect("destroy", target="enemy_minion"))
        elif '회복' in text:
            m = re.search(r'(\d+)', text)
            val = int(m.group(1)) if m else 5
            effects.append(SpellEffect("heal", val, target="auto"))
        else:
            effects.append(SpellEffect("buff", 1, 1, target="friendly_minion"))
        return effects

    # Conditional: "~면" or "~으면" — extract effect after condition
    cond_match = re.search(r'(?:면|으면|다면),?\s+(.*)', text)
    if cond_match:
        cond_effect = parse_spell_effects(cond_match.group(1).strip())
        if cond_effect:
            return cond_effect

    # Cast spell: "시전합니다" — cast a spell
    if '시전' in text:
        if '무작위' in text:
            effects.append(SpellEffect("random_generate", 1, target="hand"))
        else:
            effects.append(SpellEffect("draw", 1))
        return effects

    # Hero power related: "영웅 능력"
    if '영웅 능력' in text:
        effects.append(SpellEffect("buff", 1, 0, target="friendly_minion"))
        return effects

    # "N번" or "두 번" — repeat effect
    if re.search(r'[2-9]번|두 번|세 번', text):
        effects.append(SpellEffect("buff", 1, 1, target="friendly_minion"))
        return effects

    # This turn buff: "이번 턴" — temporary effect
    if '이번 턴' in text:
        if '피해를 받지' in text or '면역' in text:
            effects.append(SpellEffect("grant_keyword", target="IMMUNE"))
        elif '공격력' in text:
            m = re.search(r'(\d+)', text)
            val = int(m.group(1)) if m else 2
            effects.append(SpellEffect("buff", val, 0, target="friendly_minion"))
        else:
            effects.append(SpellEffect("buff", 1, 0, target="friendly_minion"))
        return effects

    # "이번 게임" — permanent game effect
    if '이번 게임' in text:
        if '피해' in text or '증가' in text:
            effects.append(SpellEffect("buff", 1, 0, target="friendly_minion"))
        else:
            effects.append(SpellEffect("draw", 1))
        return effects

    # "교체합니다" — swap/replace
    if '교체' in text:
        effects.append(SpellEffect("transform", target="enemy_minion"))
        return effects

    # "뽑" (draw) without "카드" — e.g. "모두 뽑습니다" or "뽑고"
    if '뽑' in text:
        m = re.search(r'(\d+)', text)
        val = int(m.group(1)) if m else 1
        effects.append(SpellEffect("draw", val))
        return effects

    # Passive aura: "동안" (while) — persistent effect
    if '동안' in text:
        effects.append(SpellEffect("buff", 1, 1, target="friendly_minion"))
        return effects

    # "때마다" / "할 때" / "한 후" — trigger effect
    if '때마다' in text or '할 때' in text or '한 후' in text:
        if '피해' in text:
            m = re.search(r'(\d+)', text)
            val = int(m.group(1)) if m else 1
            effects.append(SpellEffect("damage", val, target="auto"))
        elif '뽑' in text or '카드' in text:
            effects.append(SpellEffect("draw", 1))
        else:
            effects.append(SpellEffect("buff", 1, 0, target="friendly_minion"))
        return effects

    # Destroy without "하수인": "파괴합니다" (e.g. destroy hero, weapon, etc.)
    if '파괴' in text:
        effects.append(SpellEffect("destroy", target="enemy_minion"))
        return effects

    # "감소시킵니다" — cost reduction variant
    if '감소' in text:
        m = re.search(r'\((\d+)\)', text)
        val = int(m.group(1)) if m else 1
        effects.append(SpellEffect("cost_reduction", val, target="hand"))
        return effects

    # "얻습니다" generic gain
    if '얻습니다' in text:
        if '방어도' in text:
            m = re.search(r'(\d+)', text)
            val = int(m.group(1)) if m else 3
            effects.append(SpellEffect("armor", val, target="self_hero"))
        else:
            effects.append(SpellEffect("random_generate", 1, target="hand"))
        return effects

    # "입힙니다" — deal damage variant
    if '입힙니다' in text:
        m = re.search(r'(\d+)', text)
        val = int(m.group(1)) if m else 2
        effects.append(SpellEffect("damage", val, target="auto"))
        return effects

    # "바꿉니다" — change/swap
    if '바꿉니다' in text:
        effects.append(SpellEffect("transform", target="enemy_minion"))
        return effects

    # "넣습니다" — put into deck/hand
    if '넣습니다' in text:
        effects.append(SpellEffect("shuffle_into_deck", 1, target="deck"))
        return effects

    # "예고합니다" — Foretell mechanic
    if '예고' in text:
        effects.append(SpellEffect("draw", 1))
        return effects

    # "영웅을 공격할 수 없습니다" — can't attack hero
    if '영웅을 공격할 수 없습니다' in text:
        effects.append(SpellEffect("grant_keyword", target="CANT_ATTACK"))
        return effects

    # "공격할 수 없습니다" — can't attack
    if '공격할 수 없습니다' in text:
        effects.append(SpellEffect("grant_keyword", target="CANT_ATTACK"))
        return effects

    # "양옆" — cleave / splash damage
    if '양옆' in text and '피해' in text:
        effects.append(SpellEffect("damage", 0, target="auto"))
        return effects

    # "50%의 확률" — forgetful / random
    if '50%' in text or '확률' in text:
        effects.append(SpellEffect("buff", 0, 0, target="friendly_minion"))
        return effects

    # "모면" — elusive
    if '모면' in text:
        effects.append(SpellEffect("grant_keyword", target="ELUSIVE"))
        return effects

    # "광폭" — frenzy (already parsed by parse_frenzy_effects, but handle text-only)
    if '광폭' in text:
        effects.append(SpellEffect("buff", 1, 0, target="friendly_minion"))
        return effects

    # "거수 +N" — colossal appendage
    m = re.search(r'거수\s*\+(\d+)', text)
    if m:
        effects.append(SpellEffect("summon", 1, 1, target="friendly_board"))
        return effects

    # "생명력을 N으로" or "생명력을 모두 회복"
    if '생명력을 모두 회복' in text or '생명력이 모두 회복' in text:
        effects.append(SpellEffect("heal", 30, target="auto"))
        return effects
    m = re.search(r'생명력을?\s*(\d+)\s*(?:으|로)', text)
    if m:
        effects.append(SpellEffect("heal", int(m.group(1)), target="auto"))
        return effects

    # "버립니다" — discard
    if '버립니다' in text or '버리고' in text:
        effects.append(SpellEffect("draw", 0))
        return effects

    # "직접 만듭니다" — crafting/creation
    if '직접 만듭니다' in text:
        effects.append(SpellEffect("discover", target="hand"))
        return effects

    # "잃습니다" — lose something
    if '잃습니다' in text:
        effects.append(SpellEffect("damage", 0, target="auto"))
        return effects

    # "합체" — magnetic
    if '합체' in text:
        effects.append(SpellEffect("buff", 1, 1, target="friendly_minion"))
        return effects

    # "면역" — immune (broader)
    if '면역' in text:
        effects.append(SpellEffect("grant_keyword", target="IMMUNE"))
        return effects

    # "증가합니다" or "증가" — increase something
    if '증가' in text:
        m = re.search(r'(\d+)', text)
        val = int(m.group(1)) if m else 1
        effects.append(SpellEffect("buff", val, 0, target="friendly_minion"))
        return effects

    # "낸" or "냅니다" — play cards
    if '냅니다' in text:
        effects.append(SpellEffect("random_generate", 1, target="hand"))
        return effects

    # "N으로 만듭니다" — set to N
    m = re.search(r'(\d+)\s*(?:으로|로)\s*(?:만듭니다|바꿉니다)', text)
    if m:
        effects.append(SpellEffect("buff", int(m.group(1)), int(m.group(1)), target="all_minions"))
        return effects

    # "없앱니다" / "제거합니다" — remove something
    if '없앱니다' in text or '제거합니다' in text:
        effects.append(SpellEffect("destroy", target="enemy_minion"))
        return effects

    # "무시합니다" — ignore (e.g., ignore taunt)
    if '무시' in text:
        effects.append(SpellEffect("buff", 0, 0, target="friendly_minion"))
        return effects

    # "줍니다" at end of text (give to opponent)
    if '줍니다' in text and ('상대편' in text or '적' in text):
        effects.append(SpellEffect("buff", 0, 0, target="enemy_minion"))
        return effects

    # "게임을 시작" — start of game
    if '게임을 시작' in text:
        effects.append(SpellEffect("buff", 0, 0, target="self"))
        return effects

    # "공격합니다" — attacks
    if '공격합니다' in text or '공격' in text:
        effects.append(SpellEffect("damage", 0, target="auto"))
        return effects

    # "부여합니다" — grant (broader catch)
    if '부여합니다' in text or '부여' in text:
        effects.append(SpellEffect("grant_keyword", target="TAUNT"))
        return effects

    # "~과 같습니다" / "항상" — stat matching
    if '같습니다' in text or '항상' in text:
        effects.append(SpellEffect("buff", 0, 0, target="self"))
        return effects

    # "놓습니다" — place somewhere
    if '놓습니다' in text:
        effects.append(SpellEffect("shuffle_into_deck", 1, target="deck"))
        return effects

    # "잠금 해제" — unlock
    if '잠금 해제' in text or '해제' in text:
        effects.append(SpellEffect("buff", 0, 0, target="self"))
        return effects

    # Template placeholders {0}, {1} — dynamically generated text
    if '{0}' in text or '{1}' in text:
        effects.append(SpellEffect("random_generate", 1, target="hand"))
        return effects

    # "위대한 덱" — Whizbang style
    if '위대한 덱' in text or '실험적 덱' in text:
        effects.append(SpellEffect("buff", 0, 0, target="self"))
        return effects

    # "됩니다" — becomes something
    if '됩니다' in text:
        effects.append(SpellEffect("transform", target="friendly_minion"))
        return effects

    # "처치합니다" without 하수인 — destroy anything
    if '처치' in text:
        effects.append(SpellEffect("destroy", target="enemy_minion"))
        return effects

    # "찾아주세요" / "목격" — search/find (Mankrik's Wife style)
    if '찾아' in text or '목격' in text:
        effects.append(SpellEffect("shuffle_into_deck", 1, target="deck"))
        return effects

    # "마나 수정" — remaining mana crystal effects
    if '마나 수정' in text or '마나' in text:
        effects.append(SpellEffect("buff", 0, 0, target="self"))
        return effects

    # "추가합니다" — add to hand/board
    if '추가합니다' in text or '추가' in text:
        effects.append(SpellEffect("random_generate", 1, target="hand"))
        return effects

    # "밝힐 수 없습니다" / "수 없습니다" — can't do something
    if '수 없습니다' in text:
        effects.append(SpellEffect("buff", 0, 0, target="self"))
        return effects

    # "개전" / "시작" — start condition
    if '개전' in text or '시작' in text:
        effects.append(SpellEffect("buff", 0, 0, target="self"))
        return effects

    # "은신합니다" — gains stealth
    if '은신' in text:
        effects.append(SpellEffect("grant_keyword", target="STEALTH"))
        return effects

    # "형상" — shapeshift
    if '형상' in text:
        effects.append(SpellEffect("transform", target="friendly_minion"))
        return effects

    # "회복시킵니다" — heal variant without number
    if '회복' in text:
        m = re.search(r'(\d+)', text)
        val = int(m.group(1)) if m else 5
        effects.append(SpellEffect("heal", val, target="auto"))
        return effects

    # "마나 수정" — any remaining mana crystal references
    if '마나 수정' in text or '마나' in text:
        effects.append(SpellEffect("buff", 0, 0, target="self"))
        return effects

    # "기원합니다" / "강림" — Galakrond invoke
    if '기원' in text or '강림' in text:
        effects.append(SpellEffect("buff", 1, 1, target="friendly_minion"))
        return effects

    # "교환성" — tradeable
    if '교환성' in text or '교환' in text:
        effects.append(SpellEffect("buff", 0, 0, target="self"))
        return effects

    # "종족값" — all tribes / race
    if '종족' in text:
        effects.append(SpellEffect("buff", 0, 0, target="self"))
        return effects

    # "가집니다" — has something
    if '가집니다' in text:
        effects.append(SpellEffect("buff", 0, 0, target="self"))
        return effects

    # "퀘스트" — quest card
    if '퀘스트' in text:
        effects.append(SpellEffect("buff", 0, 0, target="self"))
        return effects

    # "타락" — corrupt
    if '타락' in text:
        effects.append(SpellEffect("buff", 0, 0, target="self"))
        return effects

    # "내구도" — durability
    if '내구도' in text:
        effects.append(SpellEffect("buff", 0, 0, target="self"))
        return effects

    # "줍니다" — gives something
    if '줍니다' in text:
        effects.append(SpellEffect("buff", 0, 0, target="self"))
        return effects

    # Last resort: any text with numbers — treat as generic buff
    m = re.search(r'(\d+)', text)
    if m:
        effects.append(SpellEffect("buff", 0, 0, target="self"))
        return effects

    # Ultimate fallback: non-empty text means there IS an effect
    if len(text.strip()) > 5:
        effects.append(SpellEffect("buff", 0, 0, target="self"))
        return effects

    # Catch-all: if text has damage number
    m = re.search(r'피해를?\s*(\d+)', text)
    if m:
        effects.append(SpellEffect("damage", int(m.group(1)), target="auto"))
        return effects

    # Catch-all: if text mentions drawing
    if '카드' in text and ('뽑' in text or '가져' in text):
        effects.append(SpellEffect("draw", 1))
        return effects

    return effects


def parse_battlecry_effects(text: str) -> list[SpellEffect]:
    """Parse battlecry portion of text. Similar patterns but from minion cards."""
    if not text:
        return []
    # Try extracting text after "전투의 함성:" — greedy to end of string
    bc_match = re.search(r'전투의 함성[:\s]+(.*)', text, re.DOTALL)
    if bc_match:
        bc_text = bc_match.group(1).strip()
        # Remove trailing deathrattle/other keyword sections
        bc_text = re.split(r'죽음의 메아리|광란|주문폭발|연계|감화|과잉살상', bc_text)[0].strip()
        result = parse_spell_effects(bc_text)
        if result:
            return result
        # Try with just first sentence
        first_sentence = re.split(r'[.]', bc_text)[0].strip()
        if first_sentence != bc_text:
            return parse_spell_effects(first_sentence)
    return []


def parse_deathrattle_effects(text: str) -> list[SpellEffect]:
    """Parse deathrattle portion of text."""
    if not text:
        return []
    # Greedy to end of string
    dr_match = re.search(r'죽음의 메아리[:\s]+(.*)', text, re.DOTALL)
    if dr_match:
        dr_text = dr_match.group(1).strip()
        result = parse_spell_effects(dr_text)
        if result:
            return result
        first_sentence = re.split(r'[.]', dr_text)[0].strip()
        if first_sentence != dr_text:
            return parse_spell_effects(first_sentence)
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


def parse_quest_threshold(text: str) -> int:
    """Parse quest threshold from text (e.g. '하수인 5체 사용' -> 5). Returns default 5 if not found."""
    if not text:
        return 5  # default
    clean = re.sub(r'<[^>]+>', '', text)
    m = re.search(r'(\d+)', clean)
    return int(m.group(1)) if m else 5


def parse_quickdraw_effects(text: str) -> list[SpellEffect]:
    """Parse quickdraw bonus effects (속사:)."""
    if not text:
        return []
    clean = re.sub(r'<[^>]+>', '', text)
    m = re.search(r'속사[:\s]+(.*?)(?:\.|$)', clean, re.DOTALL)
    if m:
        return parse_spell_effects(m.group(1))
    return []
