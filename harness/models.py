from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class UpdateSpec:
    """Planner output: what needs updating."""
    new_cards: list[dict] = field(default_factory=list)
    changed_cards: list[dict] = field(default_factory=list)
    missing_handlers: list[str] = field(default_factory=list)
    unparsed_spells: list[dict] = field(default_factory=list)
    db_card_count: int = 0
    api_card_count: int = 0
    handler_coverage: float = 0.0
    spell_coverage: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def is_empty(self) -> bool:
        return (not self.new_cards and not self.changed_cards
                and not self.missing_handlers and not self.unparsed_spells)

    def summary(self) -> str:
        lines = ["=== Update Spec ==="]
        lines.append(f"DB cards: {self.db_card_count}, API cards: {self.api_card_count}")
        lines.append(f"New cards: {len(self.new_cards)}")
        lines.append(f"Changed cards: {len(self.changed_cards)}")
        lines.append(f"Missing handlers: {len(self.missing_handlers)}")
        lines.append(f"Unparsed spells: {len(self.unparsed_spells)}")
        lines.append(f"Handler coverage: {self.handler_coverage:.1%}")
        lines.append(f"Spell coverage: {self.spell_coverage:.1%}")
        return "\n".join(lines)


@dataclass
class QAFeedback:
    """Evaluator output: validation results."""
    passed: bool = True
    round_num: int = 0
    tests_total: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    test_failures: list[str] = field(default_factory=list)
    stress_test_passed: bool = True
    stress_test_errors: list[str] = field(default_factory=list)
    card_coverage: float = 0.0
    spell_coverage: float = 0.0
    meta_meaningful: bool = True
    details: str = ""

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        lines = [f"=== QA Feedback (Round {self.round_num}) — {status} ==="]
        lines.append(f"Tests: {self.tests_passed}/{self.tests_total}")
        if self.test_failures:
            lines.append(f"Failures: {', '.join(self.test_failures[:5])}")
        lines.append(f"Stress test: {'PASS' if self.stress_test_passed else 'FAIL'}")
        lines.append(f"Card coverage: {self.card_coverage:.1%}")
        lines.append(f"Spell coverage: {self.spell_coverage:.1%}")
        lines.append(f"Meta meaningful: {self.meta_meaningful}")
        return "\n".join(lines)


@dataclass
class RunResult:
    """Orchestrator final output."""
    status: str  # "PASS", "FAIL_MAX_ROUNDS", "NO_UPDATES_NEEDED", "ERROR"
    rounds: int = 0
    spec: UpdateSpec | None = None
    feedback: QAFeedback | None = None
    duration_seconds: float = 0.0
    error: str = ""

    def summary(self) -> str:
        lines = [f"=== Harness Run: {self.status} ==="]
        lines.append(f"Rounds: {self.rounds}")
        lines.append(f"Duration: {self.duration_seconds:.1f}s")
        if self.error:
            lines.append(f"Error: {self.error}")
        return "\n".join(lines)


@dataclass
class GeneratorResult:
    """Generator output per round."""
    cards_synced: int = 0
    handlers_generated: int = 0
    patterns_generated: int = 0
    meta_run: bool = False
    errors: list[str] = field(default_factory=list)
