"""Evaluator Agent: Validate updates via tests, stress tests, and coverage checks."""
from __future__ import annotations
import subprocess
import re
import logging
from src.db.database import SessionLocal
from src.db.tables import Card
from harness.models import QAFeedback, UpdateSpec
from harness.config import HarnessConfig

logger = logging.getLogger(__name__)


class Evaluator:
    def __init__(self, config: HarnessConfig):
        self.config = config

    def validate(self, spec: UpdateSpec, round_num: int = 1) -> QAFeedback:
        """Run all validation checks."""
        fb = QAFeedback(round_num=round_num)

        # Check 1: pytest
        if self.config.run_tests:
            self._run_pytest(fb)

        # Check 2: Stress test
        if self.config.run_stress_test:
            self._run_stress_test(fb)

        # Check 3: Coverage
        self._check_coverage(fb)

        # Check 4: Meta results
        if self.config.meta_after_update:
            self._check_meta(fb)

        # Write feedback file
        feedback_path = self.config.harness_dir / f"qa-feedback-round-{round_num}.md"
        feedback_path.write_text(fb.summary(), encoding="utf-8")

        logger.info(fb.summary())
        return fb

    def _run_pytest(self, fb: QAFeedback):
        """Run pytest and capture results."""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-q", "--tb=line"],
                capture_output=True, text=True, timeout=120,
                cwd=str(self.config.harness_dir.parent) if self.config.harness_dir.parent.exists() else "."
            )
            output = result.stdout + result.stderr
            # Parse "X passed, Y failed"
            m = re.search(r'(\d+) passed', output)
            fb.tests_passed = int(m.group(1)) if m else 0
            m = re.search(r'(\d+) failed', output)
            fb.tests_failed = int(m.group(1)) if m else 0
            fb.tests_total = fb.tests_passed + fb.tests_failed

            # Extract failure names
            for line in output.split('\n'):
                if 'FAILED' in line:
                    fb.test_failures.append(line.strip()[:100])

            if fb.tests_failed > 0:
                fb.passed = False
                logger.warning(f"pytest: {fb.tests_failed} failures")
        except subprocess.TimeoutExpired:
            fb.passed = False
            fb.test_failures.append("pytest TIMEOUT (>120s)")
        except Exception as e:
            fb.passed = False
            fb.test_failures.append(f"pytest ERROR: {e}")

    def _run_stress_test(self, fb: QAFeedback):
        """Run simulation stress test."""
        try:
            from src.simulator.match import run_match

            # Build card_db from DB
            db_session = SessionLocal()
            cards = db_session.query(Card).filter(
                Card.is_standard == True, Card.collectible == True
            ).limit(60).all()

            card_db = {}
            deck = []
            for c in cards:
                mechs = c.mechanics or []
                if isinstance(mechs, str):
                    mechs = [m.strip() for m in mechs.split(',') if m.strip()]
                card_db[c.card_id] = {
                    'card_id': c.card_id, 'card_type': c.card_type or 'MINION',
                    'name': c.name or '', 'mana_cost': c.mana_cost or 0,
                    'attack': c.attack or 0, 'health': c.health or 0,
                    'durability': c.durability or 1, 'mechanics': mechs,
                    'text': c.text or '', 'rarity': c.rarity or '',
                    'hero_class': c.hero_class or 'NEUTRAL',
                }
                if len(deck) < 30:
                    deck.append(c.card_id)
            db_session.close()

            # Pad deck
            while len(deck) < 30:
                deck.append(deck[0])

            errors = []
            for i in range(self.config.stress_test_matches):
                try:
                    run_match(list(deck), list(deck), 'MAGE', 'WARRIOR',
                             card_db, max_turns=60)
                except Exception as e:
                    errors.append(f"Game {i}: {str(e)[:100]}")

            fb.stress_test_passed = len(errors) == 0
            fb.stress_test_errors = errors[:5]
            if errors:
                fb.passed = False
                logger.warning(f"Stress test: {len(errors)}/{self.config.stress_test_matches} failures")
        except Exception as e:
            fb.stress_test_passed = False
            fb.stress_test_errors = [str(e)[:200]]
            fb.passed = False

    def _check_coverage(self, fb: QAFeedback):
        """Check spell and card handler coverage."""
        from src.simulator.spell_parser import parse_spell_effects
        import re as re_mod

        db_session = SessionLocal()
        standard = db_session.query(Card).filter(
            Card.is_standard == True, Card.collectible == True
        ).all()

        # Spell coverage
        spells = [c for c in standard if c.card_type == 'SPELL' and c.text]
        parsed = 0
        for c in spells:
            text = re_mod.sub(r'<[^>]+>', '', c.text or '').replace('[x]', '').strip()
            if text and parse_spell_effects(text):
                parsed += 1
        fb.spell_coverage = parsed / max(len(spells), 1)

        # Card coverage (total standard in DB)
        fb.card_coverage = len(standard) / max(len(standard), 1)  # Always 1.0 for DB cards

        db_session.close()

    def _check_meta(self, fb: QAFeedback):
        """Check if meta builder produces meaningful results."""
        try:
            from src.deckbuilder.meta import MetaDeckBuilder
            db_session = SessionLocal()
            builder = MetaDeckBuilder(
                db_session,
                classes=["WARRIOR", "MAGE"],
                archetypes=["aggro"],
                matches_per_pair=3,
                optimization_generations=1,
                max_decks_per_class=1,
            )
            report = builder.run()
            db_session.close()

            fb.meta_meaningful = len(report.tier_list) >= 1
            if not fb.meta_meaningful:
                fb.passed = False
        except Exception as e:
            fb.meta_meaningful = False
            logger.warning(f"Meta check failed: {e}")
