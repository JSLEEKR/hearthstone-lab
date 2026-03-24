import pytest
from unittest.mock import patch, MagicMock
from src.scheduler.jobs import create_scheduler, job_update_tierlist


class TestScheduler:
    def test_create_scheduler(self):
        scheduler = create_scheduler()
        jobs = scheduler.get_jobs()
        assert len(jobs) == 3
        job_ids = [j.id for j in jobs]
        assert "sync_cards" in job_ids
        assert "scrape_hsreplay" in job_ids
        assert "update_tierlist" in job_ids

    def test_job_update_tierlist(self):
        with patch("src.db.database.SessionLocal") as mock_session_cls, \
             patch("src.tierlist.calculator.TierCalculator") as mock_calc_cls, \
             patch("src.tierlist.ranker.TierRanker") as mock_ranker_cls, \
             patch("src.tierlist.history.TierHistoryTracker") as mock_tracker_cls:
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            mock_calc = MagicMock()
            mock_calc_cls.return_value = mock_calc
            mock_calc.get_deck_winrates.return_value = []

            mock_ranker = MagicMock()
            mock_ranker_cls.return_value = mock_ranker
            mock_ranker.rank_decks.return_value = []

            mock_tracker = MagicMock()
            mock_tracker_cls.return_value = mock_tracker

            job_update_tierlist()
            mock_db.close.assert_called_once()
