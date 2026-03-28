"""Orchestrator: Coordinates Planner -> Generator -> Evaluator pipeline."""
from __future__ import annotations
import time
import json
import logging
from harness.config import HarnessConfig
from harness.models import RunResult, UpdateSpec, QAFeedback
from harness.planner import Planner
from harness.generator import Generator
from harness.evaluator import Evaluator

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, config: HarnessConfig | None = None):
        self.config = config or HarnessConfig()
        self.planner = Planner(self.config)
        self.generator = Generator(self.config)
        self.evaluator = Evaluator(self.config)

    def run(self, dry_run: bool = False) -> RunResult:
        """Execute the full Planner -> Generator -> Evaluator pipeline."""
        start = time.time()
        logger.info("=== Harness: Starting ===")

        # Phase 1: Planning
        logger.info("Phase 1: Planner analyzing...")
        try:
            spec = self.planner.analyze()
        except Exception as e:
            return RunResult(status="ERROR", error=f"Planner failed: {e}",
                           duration_seconds=time.time() - start)

        # Write spec
        spec_path = self.config.harness_dir / "update-spec.md"
        spec_path.write_text(spec.summary(), encoding="utf-8")

        if dry_run:
            return RunResult(status="DRY_RUN", spec=spec,
                           duration_seconds=time.time() - start)

        if spec.is_empty():
            logger.info("No updates needed.")
            return RunResult(status="NO_UPDATES_NEEDED", spec=spec,
                           duration_seconds=time.time() - start)

        # Phase 2+3: Generator -> Evaluator loop
        last_feedback = None
        for round_num in range(1, self.config.max_rounds + 1):
            logger.info(f"=== Round {round_num}/{self.config.max_rounds} ===")

            # Generator
            logger.info(f"  Generator executing...")
            gen_result = self.generator.execute(spec, feedback=last_feedback)
            if gen_result.errors:
                logger.warning(f"  Generator errors: {gen_result.errors}")

            # Evaluator
            logger.info(f"  Evaluator validating...")
            feedback = self.evaluator.validate(spec, round_num=round_num)
            last_feedback = feedback

            if feedback.passed:
                logger.info(f"  PASS on round {round_num}")
                result = RunResult(
                    status="PASS", rounds=round_num, spec=spec,
                    feedback=feedback,
                    duration_seconds=time.time() - start,
                )
                self._save_run_log(result)
                return result
            else:
                logger.warning(f"  FAIL on round {round_num}")

        result = RunResult(
            status="FAIL_MAX_ROUNDS", rounds=self.config.max_rounds,
            spec=spec, feedback=last_feedback,
            duration_seconds=time.time() - start,
        )
        self._save_run_log(result)
        return result

    def _save_run_log(self, result: RunResult):
        """Save run result to .harness/run-log.json."""
        log_path = self.config.harness_dir / "run-log.json"
        entry = {
            "status": result.status,
            "rounds": result.rounds,
            "duration": result.duration_seconds,
            "error": result.error,
        }
        # Append to existing log
        history = []
        if log_path.exists():
            try:
                history = json.loads(log_path.read_text())
            except Exception:
                pass
        history.append(entry)
        log_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
