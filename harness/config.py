from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import os


@dataclass
class HarnessConfig:
    max_rounds: int = 3
    harness_dir: Path = field(default_factory=lambda: Path(".harness"))
    run_tests: bool = True
    run_stress_test: bool = True
    stress_test_matches: int = 50
    min_card_coverage: float = 0.85
    meta_after_update: bool = True
    anthropic_api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    model: str = "claude-sonnet-4-20250514"

    def __post_init__(self):
        self.harness_dir.mkdir(exist_ok=True)
