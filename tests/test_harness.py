"""Integration tests for the 3-Agent Harness system."""
import pytest
from unittest.mock import patch, MagicMock
from harness.config import HarnessConfig
from harness.models import UpdateSpec, QAFeedback, RunResult, GeneratorResult
from harness.planner import Planner
from harness.generator import Generator
from harness.evaluator import Evaluator
from harness.orchestrator import Orchestrator
from harness.prompts import load_prompt


# --- Model tests ---

class TestUpdateSpec:
    def test_empty_spec(self):
        spec = UpdateSpec()
        assert spec.is_empty()

    def test_non_empty_with_missing_handlers(self):
        spec = UpdateSpec(missing_handlers=["ABC_123"])
        assert not spec.is_empty()

    def test_non_empty_with_new_cards(self):
        spec = UpdateSpec(new_cards=[{"card_id": "X"}])
        assert not spec.is_empty()

    def test_summary_format(self):
        spec = UpdateSpec(db_card_count=100, api_card_count=110,
                         missing_handlers=["A", "B"], handler_coverage=0.9)
        s = spec.summary()
        assert "Update Spec" in s
        assert "DB cards: 100" in s
        assert "Missing handlers: 2" in s
        assert "90.0%" in s


class TestQAFeedback:
    def test_default_passes(self):
        fb = QAFeedback()
        assert fb.passed

    def test_summary_shows_status(self):
        fb = QAFeedback(passed=False, round_num=2, tests_passed=5, tests_total=7,
                       tests_failed=2, test_failures=["FAILED test_x"])
        s = fb.summary()
        assert "FAIL" in s
        assert "Round 2" in s
        assert "5/7" in s


class TestRunResult:
    def test_summary(self):
        r = RunResult(status="PASS", rounds=1, duration_seconds=3.5)
        s = r.summary()
        assert "PASS" in s
        assert "3.5s" in s

    def test_error_summary(self):
        r = RunResult(status="ERROR", error="boom")
        assert "boom" in r.summary()


class TestGeneratorResult:
    def test_defaults(self):
        r = GeneratorResult()
        assert r.cards_synced == 0
        assert r.errors == []


# --- Config tests ---

class TestHarnessConfig:
    def test_defaults(self, tmp_path):
        cfg = HarnessConfig(harness_dir=tmp_path / ".harness")
        assert cfg.max_rounds == 3
        assert cfg.run_tests is True
        assert (tmp_path / ".harness").exists()


# --- Prompts tests ---

class TestPrompts:
    def test_load_existing_prompt(self):
        text = load_prompt("planner_system")
        assert "Planner" in text

    def test_load_missing_prompt(self):
        text = load_prompt("nonexistent_prompt_xyz")
        assert text == ""


# --- Planner tests ---

class TestPlanner:
    @patch("harness.planner.SessionLocal")
    def test_analyze_returns_spec(self, mock_session_cls):
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        # Create mock cards
        mock_card = MagicMock()
        mock_card.card_id = "TEST_001"
        mock_card.is_standard = True
        mock_card.collectible = True
        mock_card.rarity = "LEGENDARY"
        mock_card.card_type = "MINION"
        mock_card.text = "Do something"
        mock_card.name = "Test Card"
        mock_db.query.return_value.all.return_value = [mock_card]

        with patch("src.simulator.card_handlers.CARD_HANDLERS", {}), \
             patch("src.simulator.card_handlers.TITAN_HANDLERS", {}), \
             patch("src.simulator.spell_parser.parse_spell_effects", return_value=[]):
            cfg = HarnessConfig(harness_dir=HarnessConfig.__dataclass_fields__["harness_dir"].default_factory())
            planner = Planner(cfg)
            spec = planner.analyze()

        assert isinstance(spec, UpdateSpec)
        assert spec.db_card_count == 1
        assert "TEST_001" in spec.missing_handlers


# --- Generator tests ---

class TestGenerator:
    def test_execute_no_changes(self, tmp_path):
        cfg = HarnessConfig(harness_dir=tmp_path / ".harness", meta_after_update=False)
        gen = Generator(cfg)
        spec = UpdateSpec()  # empty
        result = gen.execute(spec)
        assert isinstance(result, GeneratorResult)
        assert result.cards_synced == 0

    def test_execute_logs_feedback(self, tmp_path):
        cfg = HarnessConfig(harness_dir=tmp_path / ".harness", meta_after_update=False)
        gen = Generator(cfg)
        spec = UpdateSpec()
        fb = QAFeedback(test_failures=["FAILED test_foo"])
        result = gen.execute(spec, feedback=fb)
        assert isinstance(result, GeneratorResult)


# --- Orchestrator tests ---

class TestOrchestrator:
    @patch.object(Planner, "analyze")
    def test_dry_run(self, mock_analyze, tmp_path):
        mock_analyze.return_value = UpdateSpec(db_card_count=100)
        cfg = HarnessConfig(harness_dir=tmp_path / ".harness")
        orch = Orchestrator(cfg)
        result = orch.run(dry_run=True)
        assert result.status == "DRY_RUN"
        assert result.spec.db_card_count == 100

    @patch.object(Planner, "analyze")
    def test_no_updates_needed(self, mock_analyze, tmp_path):
        mock_analyze.return_value = UpdateSpec()  # empty
        cfg = HarnessConfig(harness_dir=tmp_path / ".harness")
        orch = Orchestrator(cfg)
        result = orch.run()
        assert result.status == "NO_UPDATES_NEEDED"

    @patch.object(Evaluator, "validate")
    @patch.object(Generator, "execute")
    @patch.object(Planner, "analyze")
    def test_pass_on_first_round(self, mock_analyze, mock_execute, mock_validate, tmp_path):
        mock_analyze.return_value = UpdateSpec(missing_handlers=["X"])
        mock_execute.return_value = GeneratorResult()
        mock_validate.return_value = QAFeedback(passed=True)
        cfg = HarnessConfig(harness_dir=tmp_path / ".harness")
        orch = Orchestrator(cfg)
        result = orch.run()
        assert result.status == "PASS"
        assert result.rounds == 1

    @patch.object(Evaluator, "validate")
    @patch.object(Generator, "execute")
    @patch.object(Planner, "analyze")
    def test_fail_max_rounds(self, mock_analyze, mock_execute, mock_validate, tmp_path):
        mock_analyze.return_value = UpdateSpec(missing_handlers=["X"])
        mock_execute.return_value = GeneratorResult()
        mock_validate.return_value = QAFeedback(passed=False)
        cfg = HarnessConfig(harness_dir=tmp_path / ".harness", max_rounds=2)
        orch = Orchestrator(cfg)
        result = orch.run()
        assert result.status == "FAIL_MAX_ROUNDS"
        assert result.rounds == 2

    @patch.object(Planner, "analyze", side_effect=RuntimeError("db error"))
    def test_planner_error(self, mock_analyze, tmp_path):
        cfg = HarnessConfig(harness_dir=tmp_path / ".harness")
        orch = Orchestrator(cfg)
        result = orch.run()
        assert result.status == "ERROR"
        assert "Planner failed" in result.error

    @patch.object(Evaluator, "validate")
    @patch.object(Generator, "execute")
    @patch.object(Planner, "analyze")
    def test_run_log_saved(self, mock_analyze, mock_execute, mock_validate, tmp_path):
        mock_analyze.return_value = UpdateSpec(missing_handlers=["X"])
        mock_execute.return_value = GeneratorResult()
        mock_validate.return_value = QAFeedback(passed=True)
        harness_dir = tmp_path / ".harness"
        cfg = HarnessConfig(harness_dir=harness_dir)
        orch = Orchestrator(cfg)
        orch.run()
        import json
        log = json.loads((harness_dir / "run-log.json").read_text())
        assert len(log) == 1
        assert log[0]["status"] == "PASS"
