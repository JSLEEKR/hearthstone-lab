import pytest
from src.scheduler.jobs import create_scheduler


class TestScheduler:
    def test_create_scheduler(self):
        scheduler = create_scheduler()
        jobs = scheduler.get_jobs()
        assert len(jobs) == 1
        job_ids = [j.id for j in jobs]
        assert "sync_cards" in job_ids
