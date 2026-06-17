from datetime import datetime, timezone

from app.agent.scheduler import is_quiet_hour
from app.config import settings


def test_quiet_hours_use_configured_timezone(monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_timezone", "America/New_York")

    assert is_quiet_hour(datetime(2026, 1, 1, 12, tzinfo=timezone.utc))
    assert not is_quiet_hour(datetime(2026, 1, 1, 15, tzinfo=timezone.utc))
