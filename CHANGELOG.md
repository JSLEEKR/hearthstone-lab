# Changelog

## 3-Agent Harness (2026-03-28)
- `feat` 3-agent harness — Planner/Generator/Evaluator 자동 업데이트 파이프라인
- `fix` 하네스 nav 숨김 (개발자 전용), 쓰레기 덱 정리

## UI Overhaul (2026-03-26)
- `feat` UI 전면 개편 — 티어 리스트, 덱 프리뷰, 마나 커브, 메타/옵티마이저 페이지
- `fix` ZeroDivisionError 카드 검색 방지, MCTS 인스턴스화 최적화
- `fix` MinionState mechanics → boolean 필드 자동 동기화

## QA & User Fixes (2026-03-26)
- `fix` 10개 사용자 이슈 — 클래스 검증, 덱 삭제, API 개선
- `fix` QA 버그 — HTTP 상태 코드, 입력 검증, CORS, 30장 제한

## Game Accuracy (2026-03-26)
- `fix` 16개 게임 정확도 개선 — 전투, 주문, 영웅 능력, AI 타겟팅
- `fix` 죽음의 메아리 데미지 → 보드 비면 영웅 타격 + 확장 DR 효과
- `fix` "모든 적" AoE → 영웅 포함, 마나 음수 방지, 독성 토템 수정

## AI Tuning — 10 Rounds (2026-03-26)
- `fix(R1)` AI 공격 스코어링 — 페이스 데미지 + 레탈 감지
- `fix(R2)` 페이스 우선순위 강화, 약한 트레이드 감소
- `fix(R3)` 영웅 능력 마나 관리 — HP+카드 동시 가능하면 HP 먼저
- `fix(R4)` 비밀 시스템 개선 — 폭발 함정 AoE, 얼리기 함정
- `fix(R5)` 복합 주문 파싱 — 강타(3데미지+3방어도), 신성화
- `fix(R6)` 평가 가중치 조정 — 영웅 HP 1.2x, 보드 HP 1.2x
- `fix(R7)` 후반 페이스 긴급 보너스 (10턴+)
- `fix(R8)` 작은 하수인 트레이드 밸런스 복원
- `fix(R9)` 방어도/HP 분리 평가, 덱 사이즈 팩터
- `fix(R10)` 후반 긴급도 스케일링, 0공 하수인 패널티

## Card Optimizer (2026-03-26)
- `feat` 실제 카드 추적 — 드로우/플레이/보드 임팩트 per-card 통계
- `feat` 시뮬레이션 기반 옵티마이저 — 약한 카드 감지 + 교체 검증
- `fix` 드로우 카운트 set → dict 변경, play_rate 1.0 캡

## Meta Deck Builder (2026-03-26)
- `feat` 메타 덱 빌더 — 레시피(15 아키타입 × 11 클래스), 시너지 스코어링, 진화 최적화
- `feat` 래더 킹 — 가중 승률 최적화 + 나쁜 상성 패널티
- `feat` 대회 라인업 — 컨퀘스트(Bo5, 4덱, 1밴) 시뮬레이션 + 밴 전략

## 100% Card Coverage (2026-03-26)
- `feat` 스펠 파서 확장 — 63% → 87.4% → 100% (7886/7886장)
- `feat` 게임 상태 추적 — played_cards, spells_cast, corpses, battlecry/spell modifiers
- `fix` 카드 핸들러 전면 재구현 — 근사치/단순화 제거

## Card Handlers (2026-03-26)
- `feat` 12개 타이탄 카드 — 각 3개 고유 능력 구현
- `feat` 61개 레전더리 핸들러 레지스트리
- `fix` 18개 단순화된 핸들러 재구현

## Simulator Engine (2026-03-26)
- `feat` 48개 키워드 메카닉 구현 (Taunt, Divine Shield, Charge, Rush, ...)
- `feat` 3단계 AI 시스템 — RuleBasedAI, ScoreBasedAI, MCTSAI
- `feat` 라운드 로빈 토너먼트 + 통계 출력
- `feat` 보드 상태 평가 함수
- `feat` 영웅 능력 11개 클래스 구현
- `feat` 비밀 트리거 시스템
- `feat` 이벤트 로그 + 게임 리플레이

## Web UI (2026-03-26)
- `feat` 7개 페이지 — 메인, 카드, 빌더, 시뮬레이션, 토너먼트, 메타, 옵티마이저
- `feat` 영한 i18n 지원
- `feat` HTMX + Alpine.js + Chart.js 인터랙티브 UI
- `feat` 덱 코드 임포트/익스포트

## Card Database (초기)
- `feat` HearthstoneJSON + Blizzard API 카드 수집기
- `feat` SQLAlchemy ORM + SQLite DB
- `feat` 7,886장 카드 (한국어 이름 100%)
- `feat` 1,558장 정규전 수집 가능 카드

## Project Foundation (초기)
- `feat` FastAPI 웹 서버
- `feat` 덱 빌딩 규칙 검증 (30장, 레전더리 1장, 클래스)
- `feat` CLI 엔트리포인트 + APScheduler
- `feat` Alembic 마이그레이션
