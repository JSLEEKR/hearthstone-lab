from src.simulator.spell_parser import parse_spell_effects, parse_battlecry_effects, parse_deathrattle_effects


class TestSpellParser:
    def test_direct_damage(self):
        effects = parse_spell_effects("피해를 6 줍니다.")
        assert len(effects) == 1
        assert effects[0].effect_type == "damage"
        assert effects[0].value == 6

    def test_aoe_all_minions(self):
        effects = parse_spell_effects("<b>모든</b> 하수인에게 피해를 4 줍니다.")
        assert effects[0].effect_type == "aoe_damage"
        assert effects[0].target == "all_minions"

    def test_aoe_enemy_minions(self):
        effects = parse_spell_effects("모든 적 하수인에게 피해를 3 줍니다.")
        assert effects[0].effect_type == "aoe_damage"
        assert effects[0].target == "all_enemy_minions"

    def test_heal(self):
        effects = parse_spell_effects("체력을 8 회복합니다.")
        assert effects[0].effect_type == "heal"
        assert effects[0].value == 8

    def test_draw(self):
        effects = parse_spell_effects("카드를 3장 뽑습니다.")
        assert effects[0].effect_type == "draw"
        assert effects[0].value == 3

    def test_buff(self):
        effects = parse_spell_effects("아군 하수인 하나에게 +3/+3을 부여합니다.")
        assert effects[0].effect_type == "buff"
        assert effects[0].value == 3
        assert effects[0].value2 == 3

    def test_armor(self):
        effects = parse_spell_effects("방어도를 5 얻습니다.")
        assert effects[0].effect_type == "armor"
        assert effects[0].value == 5

    def test_destroy(self):
        effects = parse_spell_effects("하수인 하나를 파괴합니다.")
        assert effects[0].effect_type == "destroy"

    def test_enemy_hero_damage(self):
        effects = parse_spell_effects("적 영웅에게 피해를 3 줍니다.")
        assert effects[0].effect_type == "damage"
        assert effects[0].target == "enemy_hero"

    def test_dollar_sign_damage(self):
        effects = parse_spell_effects("피해를 $4 줍니다.")
        assert effects[0].value == 4

    def test_empty_text(self):
        assert parse_spell_effects("") == []
        assert parse_spell_effects(None) == []

    def test_battlecry_parse(self):
        effects = parse_battlecry_effects("<b>전투의 함성:</b> 피해를 3 줍니다.")
        assert len(effects) >= 1
        assert effects[0].effect_type == "damage"

    def test_deathrattle_parse(self):
        effects = parse_deathrattle_effects("<b>죽음의 메아리:</b> 카드를 2장 뽑습니다.")
        assert len(effects) >= 1
        assert effects[0].effect_type == "draw"
        assert effects[0].value == 2

    def test_freeze_all(self):
        effects = parse_spell_effects("모든 적 하수인을 빙결시킵니다.")
        assert effects[0].effect_type == "freeze_all"
