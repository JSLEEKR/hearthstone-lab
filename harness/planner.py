"""Planner Agent: Detect what needs updating by comparing DB vs HearthstoneJSON API."""
from __future__ import annotations
import re
import logging
from src.db.database import SessionLocal
from src.db.tables import Card
from harness.models import UpdateSpec
from harness.config import HarnessConfig

logger = logging.getLogger(__name__)


class Planner:
    def __init__(self, config: HarnessConfig):
        self.config = config

    def analyze(self) -> UpdateSpec:
        """Compare local DB state against available data, identify gaps."""
        db = SessionLocal()
        try:
            db_cards = {c.card_id: c for c in db.query(Card).all()}
            db_standard = {cid: c for cid, c in db_cards.items()
                          if c.is_standard and c.collectible}

            # Check handler coverage
            from src.simulator.card_handlers import CARD_HANDLERS, TITAN_HANDLERS
            all_handlers = set(CARD_HANDLERS.keys()) | set(TITAN_HANDLERS.keys())
            standard_legendaries = [c for c in db_standard.values()
                                    if c.rarity == "LEGENDARY" and c.card_type == "MINION"]
            missing_handlers = [c.card_id for c in standard_legendaries
                               if c.card_id not in all_handlers]
            handler_cov = 1 - len(missing_handlers) / max(len(standard_legendaries), 1)

            # Check spell coverage
            from src.simulator.spell_parser import parse_spell_effects
            standard_spells = [c for c in db_standard.values()
                              if c.card_type == "SPELL" and c.text]
            unparsed = []
            for c in standard_spells:
                text = re.sub(r'<[^>]+>', '', c.text or '').replace('[x]', '').replace('\n', ' ').strip()
                if text and not parse_spell_effects(text):
                    unparsed.append({"card_id": c.card_id, "name": c.name, "text": text[:80]})
            spell_cov = 1 - len(unparsed) / max(len(standard_spells), 1)

            spec = UpdateSpec(
                db_card_count=len(db_cards),
                api_card_count=len(db_cards),  # Will be updated if API fetch is done
                missing_handlers=missing_handlers,
                unparsed_spells=unparsed,
                handler_coverage=handler_cov,
                spell_coverage=spell_cov,
            )

            logger.info(spec.summary())
            return spec
        finally:
            db.close()
