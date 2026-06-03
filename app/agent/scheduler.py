"""APScheduler setup for proactive ticks."""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.agent.runner import run_tick
from app.config import settings

logger = logging.getLogger(__name__)

_QUIET_HOUR_START = 22  # 22:00 onward → quiet
_QUIET_HOUR_END = 8  # until 08:00 → quiet

scheduler = AsyncIOScheduler()


async def _tick_job() -> None:
    """Cron callback — no-op during quiet hours."""
    hour = datetime.now().hour
    if hour < _QUIET_HOUR_END or hour >= _QUIET_HOUR_START:
        logger.info("scheduler: quiet hours (%02d:xx), skipping tick", hour)
        return
    logger.info("scheduler: firing tick for user %s", settings.allowed_user_id)
    await run_tick(settings.allowed_user_id)


def start_scheduler() -> None:
    """Register cron jobs and start the scheduler."""
    if not settings.allowed_user_id:
        logger.warning("scheduler: allowed_user_id not set, not starting")
        return

    for hour in (9, 13, 20):
        scheduler.add_job(
            _tick_job,
            trigger="cron",
            hour=hour,
            minute=0,
            id=f"tick_{hour:02d}",
            replace_existing=True,
        )

    scheduler.start()
    logger.info("scheduler: started (ticks at 09:00, 13:00, 20:00)")


def stop_scheduler() -> None:
    """Stop the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("scheduler: stopped")
