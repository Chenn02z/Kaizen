"""Centralised app-timezone datetime helpers."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config import get_app_timezone


def app_now() -> datetime:
    """Return the current datetime in the app's configured timezone."""
    return datetime.now(get_app_timezone())


def app_date(value: datetime) -> date:
    """Return the calendar date of *value* in the app's configured timezone.

    Naive datetimes are assumed to already be in app time.
    """
    if value.tzinfo is None:
        return value.date()
    return value.astimezone(get_app_timezone()).date()


def day_start(day: date) -> datetime:
    """Return midnight of *day* in the app's configured timezone."""
    return datetime.combine(day, datetime.min.time(), tzinfo=get_app_timezone())


def app_datetime(value: datetime | None) -> datetime:
    """Convert *value* to an app-timezone-aware datetime."""
    tz: ZoneInfo = get_app_timezone()
    if value is None:
        return datetime.now(tz)
    if value.tzinfo is None:
        return value.replace(tzinfo=tz)
    return value.astimezone(tz)
