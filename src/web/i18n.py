"""Simple i18n module for English/Korean language support."""
from __future__ import annotations

SUPPORTED_LANGS = ("en", "ko")
DEFAULT_LANG = "en"

TRANSLATIONS: dict[str, dict[str, str]] = {
    # Navigation
    "nav.cards": {"en": "Card DB", "ko": "카드 DB"},
    "nav.builder": {"en": "Deck Builder", "ko": "덱빌더"},
    "nav.simulation": {"en": "Simulation", "ko": "시뮬레이션"},

    # Common
    "common.all": {"en": "All", "ko": "전체"},
    "common.standard": {"en": "Standard", "ko": "스탠다드"},
    "common.wild": {"en": "Wild", "ko": "와일드"},
    "common.format": {"en": "Format", "ko": "포맷"},
    "common.search": {"en": "Search", "ko": "검색"},
    "common.class": {"en": "Class", "ko": "직업"},
    "common.type": {"en": "Type", "ko": "유형"},
    "common.mana_cost": {"en": "Mana Cost", "ko": "마나 비용"},
    "common.rarity": {"en": "Rarity", "ko": "레어도"},
    "common.expansion": {"en": "Expansion", "ko": "확장팩"},
    "common.card_name_placeholder": {"en": "Card name...", "ko": "카드 이름..."},
    "common.previous": {"en": "Previous", "ko": "이전"},
    "common.next": {"en": "Next", "ko": "다음"},
    "common.cards_unit": {"en": "cards", "ko": "장"},
    "common.import": {"en": "Import", "ko": "가져오기"},

    # Classes
    "class.MAGE": {"en": "Mage", "ko": "마법사"},
    "class.WARRIOR": {"en": "Warrior", "ko": "전사"},
    "class.PALADIN": {"en": "Paladin", "ko": "성기사"},
    "class.HUNTER": {"en": "Hunter", "ko": "사냥꾼"},
    "class.ROGUE": {"en": "Rogue", "ko": "도적"},
    "class.PRIEST": {"en": "Priest", "ko": "사제"},
    "class.SHAMAN": {"en": "Shaman", "ko": "주술사"},
    "class.WARLOCK": {"en": "Warlock", "ko": "흑마법사"},
    "class.DRUID": {"en": "Druid", "ko": "드루이드"},
    "class.DEMONHUNTER": {"en": "Demon Hunter", "ko": "악마사냥꾼"},
    "class.DEATHKNIGHT": {"en": "Death Knight", "ko": "죽음의 기사"},
    "class.NEUTRAL": {"en": "Neutral", "ko": "중립"},

    # Card types
    "type.MINION": {"en": "Minion", "ko": "하수인"},
    "type.SPELL": {"en": "Spell", "ko": "주문"},
    "type.WEAPON": {"en": "Weapon", "ko": "무기"},
    "type.HERO": {"en": "Hero", "ko": "영웅"},
    "type.LOCATION": {"en": "Location", "ko": "장소"},

    # Rarities
    "rarity.FREE": {"en": "Free", "ko": "무료"},
    "rarity.COMMON": {"en": "Common", "ko": "일반"},
    "rarity.RARE": {"en": "Rare", "ko": "희귀"},
    "rarity.EPIC": {"en": "Epic", "ko": "영웅"},
    "rarity.LEGENDARY": {"en": "Legendary", "ko": "전설"},

    # Cards page
    "cards.title": {"en": "Card Database", "ko": "카드 데이터베이스"},
    "cards.loading": {"en": "Loading cards...", "ko": "카드를 불러오는 중..."},
    "cards.class_only": {"en": "Class only (exclude Neutral)", "ko": "직업 전용 (중립 제외)"},
    "cards.modal.mana": {"en": "Mana", "ko": "마나"},
    "cards.modal.attack": {"en": "Attack", "ko": "공격력"},
    "cards.modal.health": {"en": "Health", "ko": "체력"},
    "cards.modal.effect": {"en": "Card Effect", "ko": "카드 효과"},
    "cards.modal.mechanics": {"en": "Mechanics", "ko": "메커니즘"},
    "cards.modal.no_effect": {"en": "No effect", "ko": "효과 없음"},

    # Builder page
    "builder.title": {"en": "Deck Builder", "ko": "덱빌더"},
    "builder.ai_recommend": {"en": "AI Deck Recommend", "ko": "AI 덱 추천"},
    "builder.select_class": {"en": "Select a class", "ko": "직업을 선택하세요"},
    "builder.no_cards": {"en": "No cards found", "ko": "카드를 찾을 수 없습니다"},
    "builder.deck": {"en": "Deck", "ko": "덱"},
    "builder.click_to_add": {"en": "Click cards to add to deck", "ko": "카드를 클릭하여 덱에 추가하세요"},
    "builder.paste_code": {"en": "Paste deck code...", "ko": "덱 코드 붙여넣기..."},
    "builder.select_class_first": {"en": "Please select a class first.", "ko": "직업을 먼저 선택하세요."},
    "builder.import_failed": {"en": "Import failed", "ko": "가져오기 실패"},

    # Simulation page
    "sim.title": {"en": "Deck Simulation", "ko": "덱 시뮬레이션"},
    "sim.select_deck_a": {"en": "Select Deck A", "ko": "덱 A 선택"},
    "sim.select_deck_b": {"en": "Select Deck B", "ko": "덱 B 선택"},
    "sim.matches": {"en": "Matches", "ko": "매치"},
    "sim.run": {"en": "Run Simulation", "ko": "시뮬레이션 실행"},
    "sim.running": {"en": "Running...", "ko": "실행 중..."},
    "sim.results": {"en": "Results", "ko": "결과"},
    "sim.wins": {"en": "wins", "ko": "승"},
    "sim.draws": {"en": "Draws", "ko": "무승부"},
    "sim.select_both": {"en": "Please select both decks.", "ko": "두 덱을 모두 선택하세요."},

    # Deck detail page
    "deck.mana_curve": {"en": "Mana Curve", "ko": "마나 커브"},
    "deck.composition": {"en": "Card Composition", "ko": "카드 구성"},
    "deck.rarity_dist": {"en": "Rarity Distribution", "ko": "레어도 분포"},
    "deck.card_list": {"en": "Card List", "ko": "카드 목록"},
    "deck.copy_code": {"en": "Copy Deck Code", "ko": "덱 코드 복사"},
    "deck.copied": {"en": "Copied!", "ko": "복사됨!"},
    "deck.card_count": {"en": "Cards", "ko": "카드 수"},
}

# Set names (English)
SET_NAME_EN: dict[str, str] = {
    "CORE": "Core", "EXPERT1": "Classic", "LEGACY": "Legacy", "VANILLA": "Classic",
    "NAXX": "Naxxramas", "GVG": "Goblins vs Gnomes", "BRM": "Blackrock Mountain",
    "TGT": "The Grand Tournament", "LOE": "League of Explorers",
    "OG": "Whispers of the Old Gods", "KARA": "One Night in Karazhan",
    "GANGS": "Mean Streets of Gadgetzan", "UNGORO": "Journey to Un'Goro",
    "ICECROWN": "Knights of the Frozen Throne", "LOOTAPALOOZA": "Kobolds & Catacombs",
    "GILNEAS": "The Witchwood", "BOOMSDAY": "The Boomsday Project",
    "TROLL": "Rastakhan's Rumble", "DALARAN": "Rise of Shadows",
    "ULDUM": "Saviors of Uldum", "DRAGONS": "Descent of Dragons",
    "YEAR_OF_THE_DRAGON": "Year of the Dragon",
    "BLACK_TEMPLE": "Ashes of Outland", "SCHOLOMANCE": "Scholomance Academy",
    "DARKMOON_FAIRE": "Madness at the Darkmoon Faire",
    "THE_BARRENS": "Forged in the Barrens", "STORMWIND": "United in Stormwind",
    "ALTERAC_VALLEY": "Fractured in Alterac Valley",
    "THE_SUNKEN_CITY": "Voyage to the Sunken City",
    "REVENDRETH": "Murder at Castle Nathria",
    "RETURN_OF_THE_LICH_KING": "March of the Lich King",
    "PATH_OF_ARTHAS": "Path of Arthas",
    "BATTLE_OF_THE_BANDS": "Festival of Legends", "TITANS": "TITANS",
    "WILD_WEST": "Showdown in the Badlands",
    "WHIZBANGS_WORKSHOP": "Whizbang's Workshop",
    "ISLAND_VACATION": "Perils in Paradise",
    "EMERALD_DREAM": "Into the Emerald Dream",
    "SPACE": "The Great Dark Beyond", "TIME_TRAVEL": "Time Travel",
    "WONDERS": "Wonders", "CATACLYSM": "Cataclysm",
    "THE_LOST_CITY": "The Lost City",
    "DEMON_HUNTER_INITIATE": "Demon Hunter Initiate",
    "PLACEHOLDER_202204": "Legacy Core", "EVENT": "Events",
    "GREAT_DARK_BEYOND": "The Great Dark Beyond",
    "RETURN_TO_UN_GORO": "Return to Un'Goro",
}

SET_NAME_KO: dict[str, str] = {
    "CORE": "기본", "EXPERT1": "오리지널", "LEGACY": "레거시", "VANILLA": "클래식",
    "NAXX": "낙스라마스", "GVG": "고블린 대 노움", "BRM": "검은바위 산",
    "TGT": "대 마상시합", "LOE": "탐험가 연맹",
    "OG": "고대 신의 속삭임", "KARA": "카라잔",
    "GANGS": "비열한 거리", "UNGORO": "운고로",
    "ICECROWN": "얼어붙은 왕좌", "LOOTAPALOOZA": "코볼트와 지하 미궁",
    "GILNEAS": "마녀숲", "BOOMSDAY": "박사 붐의 폭심만만 프로젝트",
    "TROLL": "라스타칸의 대난투", "DALARAN": "달라란 대작전",
    "ULDUM": "울둠의 구원자", "DRAGONS": "용의 강림",
    "YEAR_OF_THE_DRAGON": "용의 해",
    "BLACK_TEMPLE": "황폐한 아웃랜드", "SCHOLOMANCE": "스칼로맨스 아카데미",
    "DARKMOON_FAIRE": "다크문 축제",
    "THE_BARRENS": "불모의 땅", "STORMWIND": "스톰윈드",
    "ALTERAC_VALLEY": "알터랙 계곡", "THE_SUNKEN_CITY": "침몰의 도시",
    "REVENDRETH": "레벤드레스", "RETURN_OF_THE_LICH_KING": "리치왕의 귀환",
    "PATH_OF_ARTHAS": "아서스의 길",
    "BATTLE_OF_THE_BANDS": "밴드의 전쟁", "TITANS": "타이탄",
    "WILD_WEST": "황야의 땅", "WHIZBANGS_WORKSHOP": "위즈뱅의 작업실",
    "ISLAND_VACATION": "섬 휴가", "EMERALD_DREAM": "에메랄드 꿈속으로",
    "SPACE": "거대한 어둠 너머", "TIME_TRAVEL": "시간 여행",
    "WONDERS": "경이", "CATACLYSM": "대격변",
    "THE_LOST_CITY": "잃어버린 도시",
    "DEMON_HUNTER_INITIATE": "악마사냥꾼 입문",
    "PLACEHOLDER_202204": "과거 코어셋", "EVENT": "이벤트",
    "GREAT_DARK_BEYOND": "거대한 어둠 너머",
    "RETURN_TO_UN_GORO": "운고로 귀환",
}

# Image URL locales
IMAGE_LOCALES = {"en": "enUS", "ko": "koKR"}


def t(key: str, lang: str = DEFAULT_LANG) -> str:
    """Get translation for a key."""
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(lang, entry.get(DEFAULT_LANG, key))


def get_set_name(set_code: str, lang: str = DEFAULT_LANG) -> str:
    """Get localized set name."""
    if lang == "ko":
        return SET_NAME_KO.get(set_code, set_code)
    return SET_NAME_EN.get(set_code, set_code)


def get_card_image_url(card_id: str, lang: str = DEFAULT_LANG) -> str:
    """Get card image URL for the given locale."""
    locale = IMAGE_LOCALES.get(lang, "enUS")
    return f"https://art.hearthstonejson.com/v1/render/latest/{locale}/512x/{card_id}.png"


def get_all_translations(lang: str) -> dict[str, str]:
    """Get all translations as a flat dict for template use."""
    return {key: t(key, lang) for key in TRANSLATIONS}
