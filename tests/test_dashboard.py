from datetime import datetime, timezone

from app.config import settings
from app.dashboard import DashboardData
from app.db.models import ExtractedFacts, HabitEvidenceOverride, Intervention, Log
from app.db.session import AsyncSessionLocal

USER_ID = settings.allowed_user_id


async def test_dashboard_endpoint_returns_read_model(
    client,
    db_session,
    monkeypatch,
) -> None:
    now = datetime(2026, 6, 20, 21, 0, tzinfo=timezone.utc)
    import app.dashboard as dashboard_module

    monkeypatch.setattr(dashboard_module, "utcnow", lambda: now)

    async with AsyncSessionLocal() as session:
        log_monday = Log(
            telegram_user_id=USER_ID,
            text="did leetcode on Monday",
            created_at=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
        )
        log_wednesday = Log(
            telegram_user_id=USER_ID,
            text="did leetcode and worked on the app",
            created_at=datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc),
        )
        log_saturday = Log(
            telegram_user_id=USER_ID,
            text="solved leetcode today",
            created_at=datetime(2026, 6, 20, 10, 0, tzinfo=timezone.utc),
        )
        log_old = Log(
            telegram_user_id=USER_ID,
            text="ran this morning",
            created_at=datetime(2026, 6, 16, 10, 0, tzinfo=timezone.utc),
        )
        session.add_all([log_monday, log_wednesday, log_saturday, log_old])
        await session.flush()
        session.add_all(
            [
                ExtractedFacts(
                    log_id=log_monday.id,
                    habits=["leetcode"],
                    adherence="yes",
                ),
                ExtractedFacts(
                    log_id=log_wednesday.id,
                    habits=["leetcode"],
                    adherence="yes",
                    mood="focused",
                    trigger="morning coffee",
                    context="at desk",
                ),
                ExtractedFacts(
                    log_id=log_saturday.id,
                    habits=["leetcode"],
                    adherence="yes",
                ),
                ExtractedFacts(
                    log_id=log_old.id,
                    habits=["run"],
                    adherence="yes",
                    mood="good",
                    trigger="quiet morning",
                    context="outside",
                ),
            ]
        )
        session.add(
            Intervention(
                telegram_user_id=USER_ID,
                kind="proactive",
                reason="missed gym two days in a row",
                technique="implementation intentions",
                message="Pick a fixed time for gym.",
                engaged=True,
            )
        )
        await session.commit()

    params = {"secret": settings.miniapp_secret} if settings.miniapp_secret else None
    response = await client.get("/dashboard", params=params)
    assert response.status_code == 200
    data = response.json()
    dashboard = DashboardData.model_validate(data)

    habits = {habit.name: habit for habit in dashboard.habits}
    assert habits["leetcode"].today_status == "done"
    assert habits["leetcode"].cadence_summary == "daily"
    assert [day.label for day in habits["leetcode"].week] == ["M", "T", "W", "T", "F", "S", "S"]
    assert [day.status for day in habits["leetcode"].week] == [
        "done",
        "missing",
        "done",
        "missing",
        "missing",
        "done",
        "unknown",
    ]
    assert habits["leetcode"].weekly_done_count == 3
    assert habits["leetcode"].weekly_target_count == 7
    assert habits["read"].today_status == "missing"
    assert habits["gym"].weekly_target_count == 3

    assert dashboard.recent_logs[0].text == "solved leetcode today"
    assert dashboard.recent_logs[0].habits == ["leetcode"]
    assert dashboard.recent_interventions[0].kind == "proactive"


async def test_dashboard_reveals_corrected_habit_state(
    client,
    db_session,
    monkeypatch,
) -> None:
    now = datetime(2026, 6, 17, 21, 0, tzinfo=timezone.utc)
    import app.dashboard as dashboard_module

    monkeypatch.setattr(dashboard_module, "utcnow", lambda: now)

    async with AsyncSessionLocal() as session:
        log = Log(
            telegram_user_id=USER_ID,
            text="worked out hard after lunch",
            created_at=datetime(2026, 6, 17, 12, 0, tzinfo=timezone.utc),
        )
        session.add(log)
        await session.flush()
        session.add(
            ExtractedFacts(
                log_id=log.id,
                habits=[],
                adherence=None,
            )
        )
        session.add(
            HabitEvidenceOverride(
                telegram_user_id=USER_ID,
                log_id=log.id,
                habit_name="gym",
                target_date=now.date(),
                override_status="yes",
                user_text="count that as gym",
                reason="test correction",
            )
        )
        await session.commit()

    params = {"secret": settings.miniapp_secret} if settings.miniapp_secret else None
    response = await client.get("/dashboard", params=params)
    assert response.status_code == 200
    dashboard = DashboardData.model_validate(response.json())

    habits = {habit.name: habit for habit in dashboard.habits}
    assert habits["gym"].today_status == "done"
    assert habits["gym"].is_corrected_today is True
    today = next(day for day in habits["gym"].week if day.date == now.date())
    assert today.status == "done"
    assert today.is_corrected is True
    assert "gym" in dashboard.recent_logs[0].corrected_habits
