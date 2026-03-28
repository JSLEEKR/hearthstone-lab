# GAN-Inspired 3-Agent Harness 설계 문서

> 원문: [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps) — Anthropic Engineering, 2026.03.24

---

## 1. 프로젝트 개요

### 1.1 목표

Anthropic의 Prithvi Rajasekaran이 공개한 3-에이전트 하네스 아키텍처를 Claude Agent SDK(TypeScript)로 재현한다. 1~4문장의 간단한 프롬프트를 입력하면, Planner → Generator → Evaluator 파이프라인이 자율적으로 수 시간 동안 동작하여 프로덕션 수준의 풀스택 애플리케이션을 생성한다.

### 1.2 원문 아티클 핵심 교훈 요약

1. **모델은 자기 작업을 평가하면 관대해진다** — 생성과 평가를 분리해야 한다
2. **Context anxiety** — Sonnet 4.5는 context reset이 필수였으나, Opus 4.5/4.6에서는 compaction만으로 충분
3. **Sprint contract** — Generator와 Evaluator가 각 스프린트 전 "완료 조건"을 협상
4. **파일 기반 통신** — 에이전트 간 소통은 파일 읽기/쓰기로 수행 (메시지 패싱 아님)
5. **하네스 컴포넌트는 모델 가정을 인코딩** — 모델이 개선되면 가정을 재검증하고 불필요한 scaffold를 제거

### 1.3 아티클 버전 히스토리 (V1 → V2)

| 구분 | V1 (Opus 4.5) | V2 (Opus 4.6) |
|------|---------------|---------------|
| 에이전트 수 | 3 (Planner + Generator + Evaluator) | 3 (동일, 구조 단순화) |
| Sprint 분해 | 있음 (feature별 sprint) | **제거** — 모델이 자체적으로 장시간 coherent 작업 가능 |
| Sprint contract | 매 스프린트 전 Generator↔Evaluator 협상 | 제거 |
| Evaluator 실행 | 매 스프린트 후 | **빌드 완료 후 1회** (필요시 반복) |
| Context 관리 | Context reset (세션 분리) | Compaction만 사용 (단일 연속 세션) |
| 비용/시간 (retro game maker) | $200 / 6시간 | — |
| 비용/시간 (DAW) | — | $124.70 / 3시간 50분 |

---

## 2. 시스템 아키텍처

### 2.1 전체 파이프라인 흐름

```
[User Prompt: 1~4문장]
        │
        ▼
┌──────────────┐
│   PLANNER    │  ← 프롬프트를 전체 제품 스펙으로 확장
│              │  ← 야심찬 스코프 + AI feature 포함
│              │  ← 고수준 제품 컨텍스트만 (상세 구현 X)
└──────┬───────┘
       │  출력: product-spec.md
       ▼
┌──────────────┐     ┌──────────────┐
│  GENERATOR   │◄───►│  EVALUATOR   │
│              │     │              │
│  코드 작성    │     │  Playwright로 │
│  git commit  │     │  실제 앱 테스트 │
│  자체 평가    │     │  기준별 채점    │
└──────┬───────┘     └──────┬───────┘
       │                    │
       │  빌드 완료          │  피드백 (PASS/FAIL + 상세)
       └────────►───────────┘
                    │
              반복 (FAIL 시 Generator 재작업)
                    │
                    ▼
            [최종 애플리케이션]
```

### 2.2 에이전트별 상세 설계

#### 2.2.1 Planner Agent

**역할:** 사용자의 간단한 프롬프트를 풍부한 제품 스펙으로 확장

**입력:**
- 사용자 프롬프트 (1~4문장)
- Frontend design skill (선택)

**출력 파일:** `product-spec.md`

**출력 구조:**
```
1. Overview — 제품 비전과 타겟 사용자
2. Features (10~20개) — 각 feature별:
   - 설명
   - User Stories ("As a user, I want to...")
   - Data Model (해당 시)
3. Visual Design Language — 색상, 타이포그래피, 레이아웃 원칙
4. Technical Architecture — 고수준 스택 결정 (React + Vite + FastAPI + SQLite)
5. AI Integration Points — Claude를 제품 내에서 활용하는 방법
```

**프롬프트 설계 핵심:**
- "야심찬 스코프를 가져라" — 단일 에이전트보다 훨씬 많은 feature를 기획
- "제품 컨텍스트와 고수준 기술 설계에 집중하라" — 세부 구현을 명시하면 오류가 cascade
- "AI feature를 제품에 녹여라" — Claude API를 활용한 기능 기획 포함
- "상세 기술 구현은 하지 마라" — deliverable만 제약하고 경로는 Generator에게 위임

**시스템 프롬프트 뼈대:**
```
You are a product planner. Given a brief user prompt, expand it into a
comprehensive product specification.

Rules:
- Be ambitious about scope — aim for 10-20 features across sprints
- Focus on PRODUCT context and HIGH-LEVEL technical design
- Do NOT specify granular technical implementation details
- Find opportunities to weave AI features (powered by Claude) into the spec
- Include a visual design language section
- Write user stories for each feature
- Output as a single markdown file: product-spec.md
```

#### 2.2.2 Generator Agent

**역할:** product-spec.md를 읽고 실제 코드를 작성, 빌드, 테스트

**입력:**
- `product-spec.md` (Planner 출력)
- Evaluator 피드백 (반복 시)

**출력:**
- 실제 작동하는 풀스택 애플리케이션 코드
- git commits

**기술 스택 (아티클 기준):**
- Frontend: React + Vite
- Backend: FastAPI (Python)
- DB: SQLite → PostgreSQL
- Version Control: git

**V1 동작 (Sprint 모드):**
1. product-spec.md에서 다음 스프린트 feature를 선택
2. Evaluator와 sprint contract 협상 (완료 조건 합의)
3. 코드 작성 → 자체 테스트 → git commit
4. Evaluator에게 핸드오프
5. FAIL 시 피드백 반영 후 재작업

**V2 동작 (단일 빌드 모드 — Opus 4.6):**
1. product-spec.md 전체를 읽음
2. 스스로 빌드 순서를 계획
3. 연속으로 전체 앱을 작성 (2시간+ 단일 세션)
4. 빌드 완료 후 Evaluator에게 핸드오프
5. FAIL 시 피드백 반영 후 재작업

**시스템 프롬프트 뼈대:**
```
You are a senior full-stack developer. Read product-spec.md and build the
complete application.

Rules:
- Use React + Vite for frontend, FastAPI for backend, SQLite for database
- Work through features systematically
- Make git commits after completing each logical unit
- Self-evaluate your work before considering it complete
- When building AI features, implement a proper agent with tools (not just
  API calls)
- If you receive evaluator feedback, address every issue before resubmitting

Output:
- Working application code in the project directory
- Start dev servers so the evaluator can test
```

**허용 도구:**
- `Read`, `Write`, `Edit`, `Bash`, `Glob`, `Grep` — 파일 및 터미널 전체 접근
- `WebSearch` — 기술 문서 참조 (선택)

#### 2.2.3 Evaluator Agent

**역할:** 실행 중인 앱을 Playwright로 실제 클릭/테스트하고 기준별 채점

**입력:**
- `product-spec.md`
- 실행 중인 애플리케이션 (localhost URL)
- Sprint contract (V1) 또는 전체 스펙 (V2)

**출력 파일:** `qa-feedback.md`

**평가 기준 (4가지):**

| 기준 | 가중치 | 설명 |
|------|--------|------|
| **Product Depth** | 높음 | 스펙에 명시된 feature가 실제로 구현되었는가? stub이 아닌 실제 동작하는가? |
| **Functionality** | 높음 | UI 인터랙션, API 엔드포인트, DB 상태가 정상 동작하는가? |
| **Visual Design** | 중간 | 일관된 디자인 언어, 레이아웃 품질, "AI slop" 패턴 부재 |
| **Code Quality** | 낮음 | 기본적인 코드 품질 (보통 자연스럽게 충족됨) |

**각 기준에 hard threshold 존재 — 하나라도 미달 시 FAIL**

**평가 프로세스:**
1. Playwright MCP를 통해 실제 앱 접속
2. 페이지를 직접 탐색, 클릭, 스크린샷
3. Sprint contract/스펙의 테스트 기준을 하나씩 검증
4. 기준별 점수 + 상세 피드백 작성
5. PASS/FAIL 판정
6. FAIL 시 구체적 버그 리포트 (파일 위치, 원인, 재현 방법 포함)

**시스템 프롬프트 뼈대:**
```
You are a rigorous QA engineer. Your job is to test the running application
against the product spec and grade it on four criteria.

CRITICAL RULES:
- Do NOT be lenient. If a feature is stubbed or broken, it FAILS.
- Navigate the actual app via Playwright — click buttons, fill forms, test
  edge cases
- Take screenshots for evidence
- Grade each criterion on a 1-10 scale with a hard threshold of 7
- If ANY criterion falls below threshold, the sprint FAILS
- Provide specific, actionable feedback including file paths and line numbers
- Do not talk yourself into accepting mediocre work

Criteria:
1. Product Depth (weight: high) — Are features fully implemented, not stubs?
2. Functionality (weight: high) — Do UI interactions and APIs actually work?
3. Visual Design (weight: medium) — Consistent design language? No AI slop?
4. Code Quality (weight: low) — Basic code hygiene

Output format: qa-feedback.md with per-criterion scores and detailed findings
```

**허용 도구:**
- Playwright MCP — 브라우저 자동화
- `Read`, `Bash`, `Glob`, `Grep` — 코드 인스펙션 (읽기 전용)

### 2.3 에이전트 간 통신 프로토콜

에이전트 간 소통은 **파일 기반**으로 이루어진다. 메시지 패싱이나 함수 호출이 아닌, 디스크에 파일을 쓰고 다음 에이전트가 읽는 방식이다.

```
project-root/
├── .harness/
│   ├── product-spec.md          ← Planner 출력, Generator/Evaluator 입력
│   ├── sprint-contract.md       ← Generator↔Evaluator 협상 (V1만)
│   ├── qa-feedback.md           ← Evaluator 출력, Generator 입력 (반복 시)
│   ├── qa-feedback-round-2.md   ← 2차 평가 결과
│   └── build-log.md             ← Generator가 작성하는 빌드 진행 로그
├── frontend/                    ← React + Vite
├── backend/                     ← FastAPI
├── .git/                        ← 버전 관리
└── README.md
```

---

## 3. 기술 스택 및 의존성

### 3.1 하네스 자체 (오케스트레이터)

| 구성요소 | 기술 | 비고 |
|----------|------|------|
| 언어 | TypeScript | Claude Agent SDK 공식 지원 |
| SDK | `@anthropic-ai/claude-agent-sdk` (v0.2.81+) | npm 최신 버전 사용 |
| 런타임 | Node.js 18+ | SDK 요구사항 |
| 모델 | `claude-opus-4-6` | 아티클 V2 기준. Sonnet 4.6도 테스트 가능 |
| 인증 | `ANTHROPIC_API_KEY` | .env 파일 |

### 3.2 타겟 앱 기술 스택 (Generator가 생성하는 앱)

| 구성요소 | 기술 |
|----------|------|
| Frontend | React + Vite + TypeScript |
| Backend | FastAPI (Python) |
| Database | SQLite (→ PostgreSQL 확장 가능) |
| Version Control | git |

### 3.3 Evaluator 도구

| 구성요소 | 기술 | 비고 |
|----------|------|------|
| 브라우저 자동화 | Playwright MCP Server | Evaluator가 실제 앱을 탐색 |
| 스크린샷 | Playwright 내장 | 증거 수집용 |

### 3.4 필수 MCP 서버

| MCP 서버 | 용도 | 사용 에이전트 |
|----------|------|--------------|
| Playwright MCP | 브라우저 테스트 자동화 | Evaluator |
| (선택) Filesystem MCP | 파일 접근 확장 | 전체 |

---

## 4. 오케스트레이터 설계

오케스트레이터는 3개 에이전트를 순차적으로 호출하고, 반복 로직을 관리하는 TypeScript 프로그램이다.

### 4.1 메인 루프 의사코드

```
function main(userPrompt: string, config: HarnessConfig):
    // Phase 1: Planning
    plannerResult = await runAgent("planner", {
        prompt: buildPlannerPrompt(userPrompt),
        systemPrompt: PLANNER_SYSTEM_PROMPT,
        tools: ["Read", "Write", "Bash"],
    })
    assert fileExists(".harness/product-spec.md")

    // Phase 2: Building
    for round = 1 to config.maxRounds:
        // 2a. Generator builds
        generatorPrompt = (round == 1)
            ? buildFirstBuildPrompt()
            : buildFixPrompt(round)

        generatorResult = await runAgent("generator", {
            prompt: generatorPrompt,
            systemPrompt: GENERATOR_SYSTEM_PROMPT,
            tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
            permissionMode: "bypassPermissions",
        })

        // 2b. Evaluator tests
        evaluatorResult = await runAgent("evaluator", {
            prompt: buildEvaluatorPrompt(round),
            systemPrompt: EVALUATOR_SYSTEM_PROMPT,
            tools: ["Read", "Bash", "Glob", "Grep"],
            mcpServers: [playwrightMcp],
        })

        // 2c. Check result
        if qaFeedbackPasses(".harness/qa-feedback-round-{round}.md"):
            log("✅ Build passed QA on round", round)
            break
        else:
            log("❌ Round", round, "failed. Feeding back to Generator.")

    // Phase 3: Final cleanup
    log("🎉 Application complete!")
```

### 4.2 SDK 호출 패턴

```typescript
import { query, ClaudeAgentOptions } from "@anthropic-ai/claude-agent-sdk";

async function runAgent(
  name: string,
  config: {
    prompt: string;
    systemPrompt: string;
    tools: string[];
    permissionMode?: string;
    mcpServers?: any[];
  }
): Promise<void> {
  const options: ClaudeAgentOptions = {
    systemPrompt: config.systemPrompt,
    allowedTools: config.tools,
    permissionMode: config.permissionMode ?? "bypassPermissions",
    model: "claude-opus-4-6",
    // mcpServers: config.mcpServers,  // Evaluator만
  };

  for await (const message of query({
    prompt: config.prompt,
    options,
  })) {
    // 로깅, 비용 추적 등
    logMessage(name, message);
  }
}
```

### 4.3 설정 (HarnessConfig)

```typescript
interface HarnessConfig {
  // 모델
  model: string;                    // default: "claude-opus-4-6"
  fallbackModel?: string;           // default: "claude-sonnet-4-6"

  // 반복 제어
  maxRounds: number;                // default: 3 (Generator↔Evaluator 반복 최대)
  qaThreshold: number;              // default: 7 (기준별 최소 점수, 1-10)

  // 비용 제어
  maxTokensBudget?: number;         // 총 토큰 사용량 상한
  maxDurationMinutes?: number;      // 총 실행 시간 상한

  // V1/V2 모드
  useSprints: boolean;              // true = V1 (sprint별), false = V2 (단일 빌드)
  sprintCount?: number;             // V1 모드에서의 스프린트 수

  // 타겟 앱
  appStack: {
    frontend: string;               // default: "react-vite"
    backend: string;                // default: "fastapi"
    database: string;               // default: "sqlite"
  };

  // 로깅
  logDir: string;                   // default: ".harness/logs/"
  saveTranscripts: boolean;         // default: true
}
```

---

## 5. V1 vs V2 선택 가이드

### 5.1 V1 선택 시 (Sprint 모드)

**상황:** 모델이 Sonnet 급이거나, context anxiety가 관찰되는 경우

**추가 구현 필요:**
- Sprint contract 협상 로직 (Generator가 contract 제안 → Evaluator가 검토/수정)
- Sprint별 context reset 또는 수동 세션 분리
- `sprint-contract.md` 파일 포맷 정의
- Sprint별 Evaluator 실행 및 피드백 루프

**Sprint Contract 포맷 예시:**
```markdown
## Sprint 3: Level Editor

### Implementation Scope
- Tile placement with click-drag
- Rectangle fill tool
- Entity spawn point placement and deletion
- Layer system (tile/entity)

### Test Criteria (27개 항목 예시)
1. [ ] User can place tiles by clicking on the canvas
2. [ ] Rectangle fill tool fills the selected area
3. [ ] User can select and delete entity spawn points
...

### Success Threshold
- All criteria must PASS
- If any FAIL, generator receives detailed feedback
```

### 5.2 V2 선택 시 (단일 빌드 모드) — 권장

**상황:** Opus 4.6 사용, 모델이 2시간+ 단일 세션에서 coherent하게 동작

**장점:**
- 구현이 단순 (sprint contract 협상 로직 불필요)
- 에이전트 간 핸드오프 오버헤드 감소
- SDK의 자동 compaction이 context 관리

**구현:**
- Generator는 product-spec.md를 한 번에 읽고 전체를 빌드
- Evaluator는 빌드 완료 후 1회 실행 (필요시 반복)

---

## 6. 핵심 프롬프트 엔지니어링

### 6.1 Evaluator 튜닝 — 가장 중요한 작업

아티클에서 가장 많은 반복이 필요했던 부분이 Evaluator 프롬프트 튜닝이다.

**문제:** Claude는 기본적으로 자신/동료의 작업을 관대하게 평가함
**해결:** 반복적으로 Evaluator의 로그를 읽고, 인간의 판단과 다른 부분을 수정

**튜닝 루프:**
```
1. Evaluator 실행 → 로그 확인
2. "이 버그를 봤는데 왜 PASS 줬지?" 사례 수집
3. 시스템 프롬프트에 해당 패턴을 명시적으로 FAIL로 지정
4. "표면적 테스트만 하고 edge case를 안 본다" → "모든 feature에 대해
   최소 3개의 edge case를 테스트하라" 추가
5. 반복
```

**효과적인 Evaluator 프롬프트 패턴:**
- "Do NOT talk yourself into accepting mediocre work"
- "If a feature is display-only without interactive depth, it FAILS"
- "Stub implementations are automatic failures"
- "Test at least 3 edge cases per feature"
- "Take screenshots as evidence before scoring"

### 6.2 Planner의 "Cascade 방지" 패턴

Planner가 세부 기술 구현을 명시하면 오류가 downstream으로 cascade된다.

**나쁜 예 (과도한 명시):**
```
"Use react-router v6 with createBrowserRouter, implement lazy loading
with React.lazy, use Zustand for state management with immer middleware..."
```

**좋은 예 (의도만 명시):**
```
"The app should have client-side routing with multiple pages.
State should be managed consistently across components.
The Level Editor is the most complex page and should be prioritized."
```

### 6.3 Generator의 AI Feature 구현 프롬프트

아티클에서 Generator가 앱 내에 Claude agent를 올바르게 구현하도록 하는 데 많은 튜닝이 필요했다고 언급.

**핵심 지시:**
```
When building AI features:
- Implement a proper agent with tools, not just raw API calls
- The agent should be able to drive the app's functionality through tools
- Define tools that correspond to the app's core actions
- The agent should be able to compose multiple tool calls to complete tasks
```

---

## 7. 비용 추정 및 최적화

### 7.1 원문 비용 데이터

| 프로젝트 | 하네스 | 모델 | 시간 | 비용 |
|----------|--------|------|------|------|
| Retro Game Maker | Solo | Opus 4.5 | 20분 | $9 |
| Retro Game Maker | Full (V1) | Opus 4.5 | 6시간 | $200 |
| DAW | Full (V2) | Opus 4.6 | 3시간 50분 | $124.70 |

### 7.2 DAW V2 하네스 비용 분해

| 에이전트 & 단계 | 시간 | 비용 |
|----------------|------|------|
| Planner | 4.7분 | $0.46 |
| Build (Round 1) | 2시간 7분 | $71.08 |
| QA (Round 1) | 8.8분 | $3.24 |
| Build (Round 2) | 1시간 2분 | $36.89 |
| QA (Round 2) | 6.8분 | $3.09 |
| Build (Round 3) | 10.9분 | $5.88 |
| QA (Round 3) | 9.6분 | $4.06 |
| **합계** | **3시간 50분** | **$124.70** |

### 7.3 비용 최적화 전략

1. **Planner는 Sonnet으로** — 스펙 생성은 비교적 간단한 작업. Opus 대비 ~5x 저렴
2. **Evaluator도 Sonnet 고려** — Playwright 테스트는 코드 생성보다 단순할 수 있음
3. **Generator만 Opus 유지** — 코드 생성 품질이 비용의 핵심
4. **maxRounds 제한** — 3회 초과하면 비용 대비 효과 급감
5. **token budget cap** — 런타임에서 총 토큰 사용량 모니터링 및 중단
6. **개발/테스트 시 Sonnet 전체 사용** — 하네스 로직 검증에는 Sonnet으로 충분

### 7.4 예상 비용 (Opus 4.6 기준)

| 복잡도 | 예상 시간 | 예상 비용 |
|--------|----------|----------|
| 간단한 앱 (CRUD) | 1~2시간 | $30~60 |
| 중간 앱 (에디터, 대시보드) | 3~4시간 | $100~150 |
| 복잡한 앱 (DAW, 게임 메이커) | 4~6시간 | $150~250 |

---

## 8. 구현 로드맵

### Phase 1: MVP 하네스 (1~2일)

**목표:** V2 모드로 3-에이전트 파이프라인의 기본 흐름 동작 확인

**산출물:**
- `src/orchestrator.ts` — 메인 루프
- `src/agents/planner.ts` — Planner 에이전트 래퍼
- `src/agents/generator.ts` — Generator 에이전트 래퍼
- `src/agents/evaluator.ts` — Evaluator 에이전트 래퍼
- `src/prompts/` — 시스템 프롬프트 파일들
- `src/config.ts` — HarnessConfig 정의
- `src/logger.ts` — 비용/시간 로깅

**검증:**
- 간단한 프롬프트("Build a todo app")로 전체 파이프라인 1회 실행
- Planner가 product-spec.md 생성 확인
- Generator가 코드 생성 및 서버 실행 확인
- Evaluator가 qa-feedback.md 생성 확인

### Phase 2: Evaluator 강화 (2~3일)

**목표:** Playwright MCP 연동, 평가 기준 캘리브레이션

**작업:**
- Playwright MCP 서버 연동 및 테스트
- 4가지 평가 기준 + threshold 구현
- Evaluator 프롬프트 튜닝 (few-shot examples 포함)
- PASS/FAIL 판정 로직 + 자동 반복
- 스크린샷 저장

**검증:**
- Evaluator가 실제로 버그를 발견하고 FAIL 주는지 확인
- 의도적으로 버그를 심은 앱에 대해 Evaluator가 정확히 탐지하는지 테스트

### Phase 3: 반복 루프 완성 (1~2일)

**목표:** Generator↔Evaluator 피드백 루프 자동화

**작업:**
- FAIL 시 qa-feedback.md를 Generator에게 전달하는 로직
- Round별 로깅 (시간, 비용, pass/fail)
- maxRounds, token budget, timeout 등 안전장치
- git 상태 관리 (FAIL 시 revert 옵션)

### Phase 4: 프로덕션 품질 개선 (2~3일)

**목표:** 안정성, 로깅, 비용 추적, CLI 인터페이스

**작업:**
- CLI 인터페이스 (`npx harness "Build a DAW"`)
- 실시간 진행 상황 터미널 출력 (에이전트별 상태, 비용, 시간)
- 중단/재개 기능 (세션 저장)
- 상세 비용 리포트 (에이전트별, 라운드별)
- 에러 복구 (API 장애, 타임아웃 등)

### Phase 5: V1 Sprint 모드 (선택, 2~3일)

**목표:** Sprint 분해 + Contract 협상 로직 추가

**작업:**
- Sprint contract 협상 프로토콜 구현
- Sprint별 context reset 또는 세션 분리
- Sprint별 Evaluator 실행
- V1/V2 모드 전환 config

---

## 9. 디렉토리 구조

```
harness-3agent/
├── package.json
├── tsconfig.json
├── .env                          ← ANTHROPIC_API_KEY
├── README.md
│
├── src/
│   ├── index.ts                  ← CLI 엔트리포인트
│   ├── orchestrator.ts           ← 메인 파이프라인 루프
│   ├── config.ts                 ← HarnessConfig 정의 + 기본값
│   ├── logger.ts                 ← 비용/시간/토큰 추적
│   │
│   ├── agents/
│   │   ├── base.ts               ← runAgent() 공통 SDK 래퍼
│   │   ├── planner.ts            ← Planner 호출 로직
│   │   ├── generator.ts          ← Generator 호출 로직
│   │   └── evaluator.ts          ← Evaluator 호출 + PASS/FAIL 파싱
│   │
│   ├── prompts/
│   │   ├── planner-system.md     ← Planner 시스템 프롬프트
│   │   ├── generator-system.md   ← Generator 시스템 프롬프트
│   │   ├── evaluator-system.md   ← Evaluator 시스템 프롬프트
│   │   └── templates/
│   │       ├── first-build.md    ← 1차 빌드 프롬프트 템플릿
│   │       ├── fix-build.md      ← 수정 빌드 프롬프트 템플릿
│   │       └── evaluate.md       ← 평가 프롬프트 템플릿
│   │
│   └── utils/
│       ├── files.ts              ← .harness/ 파일 읽기/쓰기 헬퍼
│       ├── cost-tracker.ts       ← 토큰 사용량 → 비용 계산
│       └── qa-parser.ts          ← qa-feedback.md에서 PASS/FAIL 파싱
│
├── workspace/                    ← Generator가 앱을 빌드하는 작업 디렉토리
│   └── .harness/                 ← 에이전트 간 통신 파일
│       ├── product-spec.md
│       ├── qa-feedback.md
│       └── build-log.md
│
└── examples/
    ├── todo-app.txt              ← "Build a simple todo app"
    ├── retro-game-maker.txt      ← 아티클 원문 프롬프트
    └── daw.txt                   ← "Build a fully featured DAW..."
```

---

## 10. 리스크 및 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| Evaluator가 너무 관대 | 버그 있는 앱이 PASS | Evaluator 프롬프트에 "자주 발생하는 관대함 패턴" 명시적 FAIL 지정. Few-shot 예제 추가. 반복 튜닝 |
| Evaluator가 너무 엄격 | 무한 반복, 비용 폭증 | maxRounds 제한 (3), 비용 cap 설정, threshold 조정 가능하게 |
| Generator가 context 내에서 길을 잃음 | 반복 작업, 미완성 feature | V2에서는 SDK compaction이 처리. 심하면 V1 sprint 모드로 전환 |
| Playwright MCP 연동 실패 | Evaluator 무력화 | Fallback으로 Generator 자체 평가 + 코드 레벨 검증 |
| API 비용 예상 초과 | 예산 소진 | token budget cap + 실시간 비용 모니터링 + 경고 알림 |
| Planner 스펙이 너무 야심적 | Generator가 시간 내 미완성 | Planner 프롬프트에 "feature 수 10~15로 제한" 조건 추가 가능 |
| 생성된 앱 서버가 시작 안 됨 | Evaluator 테스트 불가 | Generator 프롬프트에 "서버 시작 확인 후 완료 선언" 명시 |

---

## 11. 성공 기준

### MVP (Phase 1~3 완료 시)

- [ ] 1~4문장 프롬프트로 전체 파이프라인 자동 실행
- [ ] Planner가 10+ feature의 product-spec.md 생성
- [ ] Generator가 실행 가능한 풀스택 앱 생성
- [ ] Evaluator가 Playwright로 실제 테스트 수행
- [ ] FAIL 시 자동 피드백 → 수정 → 재평가 루프 동작
- [ ] 에이전트별 비용/시간 로깅

### 프로덕션 (Phase 4~5 완료 시)

- [ ] CLI로 한 줄 실행
- [ ] Solo vs Harness 품질 차이가 체감됨
- [ ] 3라운드 이내에 대부분의 빌드가 PASS
- [ ] 비용이 아티클 수준 ($100~200 범위)
- [ ] 중단/재개 가능

---

## 12. 참고 자료

- [원문 아티클](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- [이전 하네스 아티클](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- [Claude Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Claude Agent SDK Quickstart](https://platform.claude.com/docs/en/agent-sdk/quickstart)
- [SDK TypeScript Reference](https://platform.claude.com/docs/en/agent-sdk/typescript)
- [SDK GitHub (TypeScript)](https://github.com/anthropics/claude-agent-sdk-typescript)
- [Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Frontend Design Skill](https://github.com/anthropics/claude-code/blob/main/plugins/frontend-design/skills/frontend-design/SKILL.md)
