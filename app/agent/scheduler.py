"""APScheduler setup for proactive ticks."""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.agent.runner import run_tick
from app.config import get_app_timezone, settings

logger = logging.getLogger(__name__)

_QUIET_HOUR_START = 22  # 22:00 onward → quiet
_QUIET_HOUR_END = 8  # until 08:00 → quiet

scheduler = AsyncIOScheduler(timezone=get_app_timezone())


def is_quiet_hour(now: datetime) -> bool:
    """Return whether proactive messages should stay silent at this app-local time."""
    local_now = now.astimezone(get_app_timezone()) if now.tzinfo else now
    return local_now.hour < _QUIET_HOUR_END or local_now.hour >= _QUIET_HOUR_START


async def _tick_job() -> None:
    """Cron callback — no-op during quiet hours."""
    now = datetime.now(get_app_timezone())
    if is_quiet_hour(now):
        logger.info("scheduler: quiet hours (%02d:xx), skipping tick", now.hour)
        return
    logger.info("scheduler: firing tick for user %s", settings.allowed_user_id)
    await run_tick(settings.allowed_user_id, now=now)


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
