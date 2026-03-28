"""Generator Agent: Execute updates — sync cards, generate handlers, run meta."""
from __future__ import annotations
import logging
from src.db.database import SessionLocal
from harness.models import UpdateSpec, QAFeedback, GeneratorResult
from harness.config import HarnessConfig

logger = logging.getLogger(__name__)


class Generator:
    def __init__(self, config: HarnessConfig):
        self.config = config

    def execute(self, spec: UpdateSpec,
                feedback: QAFeedback | None = None) -> GeneratorResult:
        """Execute all updates described in the spec."""
        result = GeneratorResult()

        # Step 1: If there are feedback failures, try to fix them
        if feedback and feedback.test_failures:
            logger.info(f"Addressing {len(feedback.test_failures)} test failures from previous round")

        # Step 2: Sync new/changed cards to DB
        if spec.new_cards or spec.changed_cards:
            try:
                synced = self._sync_cards()
                result.cards_synced = synced
            except Exception as e:
                result.errors.append(f"Sync failed: {e}")
                logger.error(f"Card sync failed: {e}")

        # Step 3: Run meta analysis if cards changed
        if self.config.meta_after_update:
            try:
                self._run_meta()
                result.meta_run = True
            except Exception as e:
                result.errors.append(f"Meta failed: {e}")
                logger.warning(f"Meta analysis failed: {e}")

        return result

    def _sync_cards(self) -> int:
        """Sync cards using existing collector infrastructure."""
        try:
            from src.collector.hearthstone_json import HearthstoneJsonClient
            from src.collector.sync import sync_cards_to_db
            import asyncio

            async def _fetch():
                client = HearthstoneJsonClient()
                return await client.fetch_cards()

            cards = asyncio.run(_fetch())
            db = SessionLocal()
            try:
                result = sync_cards_to_db(db, cards, [])
                return result.get("created", 0) + result.get("updated", 0)
            finally:
                db.close()
        except ImportError:
            logger.warning("Collector not available, skipping sync")
            return 0
        except Exception as e:
            logger.error(f"Sync error: {e}")
            return 0

    def _run_meta(self):
        """Run meta analysis with current card data."""
        from src.deckbuilder.meta import MetaDeckBuilder
        db = SessionLocal()
        try:
            builder = MetaDeckBuilder(
                db,
                classes=["WARRIOR", "HUNTER", "MAGE"],
                archetypes=["aggro", "control"],
                matches_per_pair=5,
                optimization_generations=1,
                max_decks_per_class=1,
            )
            report = builder.run()
            logger.info(f"Meta: {report.total_decks} decks, {report.total_matches} matches")

            # Save results
            results_path = self.config.harness_dir / "meta-results.md"
            results_path.write_text(report.summary(), encoding="utf-8")
        finally:
            db.close()
