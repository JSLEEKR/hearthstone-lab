# Hearthstone Simulator + Deck Maker + Tier List - Design Spec

## Overview

Python 기반 하스스톤 시뮬레이터, 덱메이커, 덱 티어리스트 시스템. HearthSim 생태계의 기존 라이브러리(python-hearthstone, Fireplace)를 활용하여 개발 효율을 극대화한다. HSReplay 통계와 자체 AI 시뮬레이션 결과를 합산하여 하이브리드 티어리스트를 산출한다.

## Architecture

**모놀리식 구조** - 하나의 Python 프로젝트 안에서 모듈로 분리.

```
hearthstone_deckmaker/
├── src/
│   ├── core/              # 카드 모델, 게임 규칙, 상수, 덱스트링
│   ├── collector/         # 카드 데이터 수집 + 이미지 캐시
│   ├── simulator/         # 게임 시뮬레이션 엔진 (Fireplace 기반)
│   ├── deckbuilder/       # 수동/자동 덱 빌더
│   ├── scraper/           # HSReplay 데이터 수집
│   ├── tierlist/          # 티어리스트 산출
│   ├── web/               # FastAPI + Jinja2 + HTMX 대시보드
│   ├── scheduler/         # APScheduler 일일 작업
│   └── db/                # SQLAlchemy ORM + Alembic
├── tests/
├── config.py
├── requirements.txt
└── main.py
```

## Tech Stack

| Category | Technology |
|----------|-----------|
| Language | Python 3.11+ |
| Web Framework | FastAPI + Jinja2 + HTMX + Alpine.js |
| Database | SQLAlchemy ORM (SQLite default, PostgreSQL ready) |
| Migration | Alembic |
| HTTP Client | httpx (async) |
| Scraping Fallback | Playwright |
| Scheduler | APScheduler |
| AI Algorithm | MCTS (Monte Carlo Tree Search) |
| Card Data | python-hearthstone + python-hearthstone-data |
| Simulation Base | Fireplace (reference/fork) |
| Image Processing | Pillow |
| Charts | Chart.js |
| Testing | pytest |

## Data Model

### cards
| Column | Type | Description |
|--------|------|-------------|
| id | Integer PK | Auto increment |
| card_id | String UNIQUE | 카드 문자열 ID (e.g. "EX1_116") |
| dbf_id | Integer UNIQUE | 숫자 고유 ID |
| name | String | 영문 이름 |
| name_ko | String | 한국어 이름 |
| card_type | String | MINION, SPELL, WEAPON, HERO |
| hero_class | String | 직업 |
| mana_cost | Integer | 마나 비용 |
| attack | Integer nullable | 공격력 |
| health | Integer nullable | 체력 |
| durability | Integer nullable | 내구도 (무기) |
| text | Text | 카드 텍스트 |
| rarity | String | COMMON, RARE, EPIC, LEGENDARY |
| set_name | String | 확장팩 |
| mechanics | JSON | 메커니즘 배열 |
| collectible | Boolean | 수집 가능 여부 |
| is_standard | Boolean | 스탠다드 포맷 여부 |
| json_data | JSON | 원본 JSON 데이터 |
| image_url | String | 카드 이미지 URL |
| updated_at | DateTime | 최종 업데이트 |

### decks
| Column | Type | Description |
|--------|------|-------------|
| id | Integer PK | Auto increment |
| hero_class | String | 직업 |
| name | String | 덱 이름 |
| archetype | String | 어그로, 미드레인지, 컨트롤 등 |
| format | String | standard / wild |
| deckstring | String | 하스스톤 덱 코드 |
| source | String | manual, ai_generated, hsreplay |
| created_at | DateTime | 생성일 |

### deck_cards
| Column | Type | Description |
|--------|------|-------------|
| deck_id | Integer FK | decks.id |
| card_id | String FK | cards.card_id |
| count | Integer | 1 or 2 |

### simulations
| Column | Type | Description |
|--------|------|-------------|
| id | Integer PK | Auto increment |
| deck_a_id | Integer FK | decks.id |
| deck_b_id | Integer FK | decks.id |
| winner_id | Integer FK | decks.id |
| turns | Integer | 총 턴 수 |
| played_at | DateTime | 시뮬레이션 실행일 |

### hsreplay_stats
| Column | Type | Description |
|--------|------|-------------|
| id | Integer PK | Auto increment |
| deck_id | Integer FK | decks.id |
| winrate | Float | 승률 |
| playrate | Float | 플레이율 |
| games_played | Integer | 총 게임 수 |
| collected_at | DateTime | 수집일 |

### tier_history
| Column | Type | Description |
|--------|------|-------------|
| id | Integer PK | Auto increment |
| deck_id | Integer FK | decks.id |
| tier | String | S, A, B, C, D |
| sim_winrate | Float | 시뮬레이션 승률 |
| hsreplay_winrate | Float | HSReplay 승률 |
| combined_winrate | Float | 합산 승률 |
| recorded_at | DateTime | 기록일 |

## Module Specifications

### 1. core/ - 카드 모델 & 게임 규칙

**models.py**: Card, Deck, Player, GameState 데이터 모델
- python-hearthstone enums 활용 (CardType, Rarity, GameTag 등)
- Pydantic 모델로 유효성 검증

**deckstring.py**: 덱스트링 인코딩/디코딩
- hearthstone-deckstrings 포맷 호환
- 다른 앱(HDT, HSReplay)과 덱 코드 공유 가능

**rules.py**: 덱 구성 규칙
- 덱 30장 제한
- 레전더리 1장, 일반 2장 제한
- 직업 카드 + 중립 카드만 허용
- 스탠다드/와일드 포맷 규칙

### 2. collector/ - 카드 데이터 수집

**hearthstone_json.py**: HearthstoneJSON API 클라이언트
- `https://api.hearthstonejson.com/v1/latest/koKR/cards.json` 전체 다운로드
- collectible=true 필터링
- 한국어 + 영어 이름 동시 수집

**blizzard_api.py**: Blizzard API 클라이언트
- OAuth 2.0 client credentials 토큰 발급
- 페이지네이션 전체 카드 조회
- Rate limit 대응 (딜레이, 재시도)

**sync.py**: 두 소스 병합
- card_id 기준 매칭
- 충돌 시 HearthstoneJSON 우선
- Blizzard API 보충 필드 추가
- 신규/수정/삭제 감지 후 DB 반영

**image_cache.py**: 카드 이미지 캐시
- HearthstoneJSON 이미지 API에서 카드 렌더 다운로드
- `https://art.hearthstonejson.com/v1/render/latest/koKR/512x/{card_id}.png`
- 로컬 파일 시스템 캐시 (static/card_cache/)
- 미캐시 카드만 다운로드

### 3. simulator/ - 게임 시뮬레이션 엔진

**engine.py**: 게임 엔진 (Fireplace 참조/기반)
- GameState 관리: 턴, 마나, 핸드, 보드, 덱
- 턴 진행 루프: 드로우 → 행동 → 턴 종료
- 전투 처리: 공격, 피해, 체력, 사망 처리
- 주문 처리: 대상 선택, 효과 적용
- 피로 데미지, 비밀, 무기 처리

**effects.py**: 카드 효과 시스템 (이벤트 기반)
- 이벤트: ON_PLAY, ON_SUMMON, ON_DEATH, ON_DAMAGE, ON_HEAL, ON_TURN_START, ON_TURN_END, ON_DRAW, ON_ATTACK, ON_SPELL_CAST, ON_SECRET_REVEAL
- EffectRegistry: card_id → 효과 함수 매핑
- 미등록 카드는 바닐라(스탯만)로 동작
- 점진적 구현: 키워드 → 전투의 함성/죽음의 메아리 → 복잡한 효과

**ai.py**: AI 의사결정
- MCTS (Monte Carlo Tree Search) 기반
- 가능한 행동 열거 → N회 rollout → 최고 승률 행동 선택
- 룰 기반 휴리스틱 보조 (마나 효율, 유리한 교환 우선)
- 시뮬레이션 깊이/횟수로 AI 강도 조절

**match.py**: 매치 실행
- 덱 A vs 덱 B 매치업 생성
- 셔플 → 멀리건 → 게임 루프
- 최대 45턴 제한 (무한 루프 방지)
- 결과 기록 → simulations 테이블
- 매치업당 N회 반복 (기본 100회, 설정 가능)

### 4. deckbuilder/ - 덱 빌더

**manual.py**: 수동 덱 빌더
- 카드 검색/필터 (이름, 직업, 비용, 레어도, 확장팩)
- 덱에 카드 추가/제거
- 규칙 유효성 검증
- 덱스트링 내보내기/가져오기

**auto.py**: AI 자동 덱 생성
- 시너지 분석: 메커니즘/태그 기반 카드 조합 점수
- 마나 커브 최적화
- 아키타입별 카드 풀 가중치
- 기존 메타 덱 변형 생성

**archetypes.py**: 덱 아키타입 분류
- 규칙 기반 분류: 마나 커브, 카드 비율로 어그로/미드레인지/컨트롤/콤보 분류
- HSReplay 아키타입 라벨과 매핑

### 5. scraper/ - HSReplay 데이터 수집

**api_client.py**: HSReplay 내부 API
- 프론트엔드 네트워크 탭 분석 → 내부 API 엔드포인트 호출
- 덱 승률, 플레이율, 게임 수 수집
- 스탠다드 + 와일드 모두

**web_scraper.py**: Playwright 폴백
- API 실패/변경 시 페이지 크롤링
- 동적 렌더링 대응

**parser.py**: 데이터 정규화
- 수집 데이터 → hsreplay_stats 테이블 구조로 변환
- 덱 코드로 기존 덱과 매칭 또는 신규 덱 생성

### 6. tierlist/ - 티어리스트 산출

**calculator.py**: 승률 합산
```
combined_winrate = (sim_winrate × weight_sim) + (hsreplay_winrate × weight_hsreplay)
기본: weight_sim = 0.5, weight_hsreplay = 0.5 (config.py에서 조정 가능)
```

**ranker.py**: 티어 배정
```
S: 55%+  |  A: 52~55%  |  B: 49~52%  |  C: 46~49%  |  D: 46% 미만
```
- 임계값 config로 조정 가능
- 최소 게임 수 필터 (통계적 유의미성)

**history.py**: 티어 변동 추적
- 매일 tier_history 테이블에 기록
- 변동 추이 데이터 제공 (차트용)

### 7. web/ - 웹 대시보드

**FastAPI + Jinja2 + HTMX + Alpine.js**

페이지 구성:
- **티어리스트 (/)**: 포맷 선택(스탠다드/와일드), 티어별 덱 목록, 핵심 카드 이미지, 승률, 변동 추이 Chart.js 차트
- **덱 상세 (/deck/{id})**: HDT 스타일 카드 타일 리스트, 마나 커브 차트, 매치업 승률표, 시뮬레이션 이력
- **덱빌더 (/builder)**: 카드 이미지 갤러리, 필터링, 드래그&드롭 덱 구성, 실시간 마나 커브, 덱 코드 생성/가져오기, AI 추천 버튼
- **카드 DB (/cards)**: 전체 카드 갤러리, 확장팩/직업/비용/레어도 필터, 카드 상세 모달
- **시뮬레이션 (/simulation)**: 덱 vs 덱 시뮬레이션 실행, 결과 요약, 매치업 매트릭스

HDT 스타일 카드 타일 렌더링:
```
┌──────────────────────────┐
│ (2) 산성 늪 수액괴물  ★★ │  ← 마나 비용 + 이름 + 수량
│ (3) 하수인의 칼날    ★   │     배경에 카드 아트 일부 표시
│ (5) 산성 늪 히드라   ★   │
└──────────────────────────┘
```

### 8. scheduler/ - 스케줄러

**APScheduler 일일 작업 (매일 새벽 3시):**
1. 카드 데이터 동기화 (collector/sync.py)
2. HSReplay 데이터 수집 (scraper/)
3. 메타 덱 시뮬레이션 실행 (simulator/match.py)
4. 티어리스트 재산출 (tierlist/)

## Card Effect Implementation Strategy

와일드 전체 ~3000+ collectible 카드의 효과를 점진적으로 구현:

| Phase | Scope | Examples |
|-------|-------|---------|
| 1 | 바닐라 하수인 + 기본 주문 (직접 피해, 버프) | 칠풍의 예티, 화염구 |
| 2 | 핵심 키워드 | 돌진, 도발, 은신, 생명력 흡수, 천상의 보호막, 독성 |
| 3 | 전투의 함성, 죽음의 메아리 | 불타는 전쟁 대장군, 수확 골렘 |
| 4 | 복잡한 효과 | 발견, 변형, 카드 생성, 조건부 효과 |

미구현 카드는 바닐라(스탯만)로 시뮬레이션에 참여 가능 → 시뮬레이션 정확도는 구현 단계에 따라 점진적으로 향상.

## Data Flow

```
[HearthstoneJSON] ──┐
                    ├──▶ collector/sync.py ──▶ cards DB
[Blizzard API] ─────┘
                                                  │
[HSReplay] ──▶ scraper/ ──▶ hsreplay_stats DB     │
                                │                  │
                                ▼                  ▼
                        tierlist/calculator.py ◀── simulator/match.py
                                │                       ▲
                                ▼                       │
                        tier_history DB          deckbuilder/auto.py
                                │
                                ▼
                        web/ dashboard ◀── image_cache
```

## Configuration (config.py)

```python
# Database
DATABASE_URL = "sqlite:///hearthstone.db"

# Blizzard API
BLIZZARD_CLIENT_ID = ""
BLIZZARD_CLIENT_SECRET = ""

# Simulation
SIM_MATCHES_PER_MATCHUP = 100
SIM_MAX_TURNS = 45
MCTS_ITERATIONS = 1000

# Tier List
TIER_WEIGHT_SIM = 0.5
TIER_WEIGHT_HSREPLAY = 0.5
TIER_THRESHOLDS = {"S": 55, "A": 52, "B": 49, "C": 46}

# Scheduler
SCHEDULER_CRON_HOUR = 3
SCHEDULER_CRON_MINUTE = 0

# Image Cache
IMAGE_CACHE_DIR = "src/web/static/card_cache"
IMAGE_BASE_URL = "https://art.hearthstonejson.com/v1/render/latest/koKR/512x"
```

## Sub-Project Decomposition

이 프로젝트는 6개의 서브프로젝트로 순차 구현:

1. **프로젝트 기반 구축**: 프로젝트 구조, DB 설정, config, 의존성
2. **카드 데이터 수집기**: collector 모듈 + 이미지 캐시
3. **게임 시뮬레이션 엔진**: simulator 모듈 (Fireplace 참조) + AI
4. **덱빌더**: 수동 + AI 자동 생성
5. **HSReplay 스크래퍼 + 티어리스트**: scraper + tierlist 모듈
6. **웹 대시보드 + 스케줄러**: web + scheduler 모듈

각 서브프로젝트는 독립적으로 테스트 가능하며, 순서대로 의존성을 가짐.
