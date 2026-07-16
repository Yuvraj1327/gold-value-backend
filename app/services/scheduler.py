"""Background scheduler: refreshes the gold rate every hour.

Runs in-process using APScheduler's AsyncIOScheduler, started/stopped via
the FastAPI lifespan context in `app/main.py`. A fresh scheduler instance
is created on every `start_scheduler()` call (rather than reusing one
module-level singleton) so repeated app startup/shutdown cycles — as
happens across a test suite's multiple `TestClient` instantiations — never
try to reuse a scheduler bound to an already-closed event loop.

For a multi-instance production deployment, run this job in exactly one
instance (e.g. a dedicated worker/cron dyno) to avoid duplicate writes —
see DEPLOYMENT.md.
"""
from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import get_settings
from app.core.exceptions import UpstreamServiceError
from app.core.logging_config import get_logger
from app.database.session import AsyncSessionLocal
from app.repositories.gold_rate_repository import GoldRateRepository
from app.services.gold_rate_service import GoldRateService

settings = get_settings()
logger = get_logger("app.scheduler")

_scheduler: AsyncIOScheduler | None = None


async def refresh_gold_rate_job() -> None:
    async with AsyncSessionLocal() as session:
        try:
            service = GoldRateService(GoldRateRepository(session))
            await service.refresh_rate()
            logger.info("gold_rate_refreshed")
        except UpstreamServiceError as exc:
            logger.warning("gold_rate_scheduled_refresh_failed", extra={"reason": str(exc)})
        except Exception:
            logger.error("gold_rate_scheduled_refresh_unexpected_error", exc_info=True)


def start_scheduler() -> None:
    global _scheduler

    if not settings.ENABLE_SCHEDULER:
        logger.info("scheduler_disabled_by_config")
        return

    if _scheduler is not None and _scheduler.running:
        return

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        refresh_gold_rate_job,
        trigger=IntervalTrigger(minutes=settings.GOLD_RATE_REFRESH_INTERVAL_MINUTES),
        id="refresh_gold_rate",
        replace_existing=True,
        next_run_time=None,  # first refresh happens at the interval, not instantly on boot
    )
    _scheduler.start()
    logger.info("scheduler_started")


def stop_scheduler() -> None:
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")
    _scheduler = None
