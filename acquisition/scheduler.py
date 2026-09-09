"""
Scheduler: wraps APScheduler to run dashboard.pipeline.run_cycle() every
config.FETCH_INTERVAL_SECONDS (2 min by default). Runs in-process as a
background job — no separate worker process needed for the MVP.
"""
from __future__ import annotations
import logging

from apscheduler.schedulers.background import BackgroundScheduler

import config

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_scheduler(run_cycle_fn) -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    scheduler = BackgroundScheduler(daemon=True)

    def _job():
        try:
            count = run_cycle_fn()
            logger.info("Scheduled cycle complete: %d events live", count)
        except Exception as e:
            # A single bad cycle must never kill the scheduler itself.
            logger.error("Scheduled cycle failed: %s", e)

    scheduler.add_job(
        _job,
        "interval",
        seconds=config.FETCH_INTERVAL_SECONDS,
        id="mediaos_fetch_cycle",
        max_instances=1,       # never overlap a slow cycle with the next tick
        coalesce=True,         # if we fall behind, run once, not a backlog
        next_run_time=None,    # first run handled synchronously by caller
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("Scheduler started: every %ds", config.FETCH_INTERVAL_SECONDS)
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
