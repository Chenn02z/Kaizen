from datetime import datetime, timezone

from app.config import settings
from app.dashboard import DashboardData
from app.db.models import ExtractedFacts, Intervention, Log, UserProgress
from app.db.session import AsyncSessionLocal

USER_ID = settings.allowed_user_id


async def test_dashboard_endpoint_returns_read_model(
    client,
    db_session,
    monkeypatch,
) -> None:
    now = datetime(2026, 6, 17, 21, 0, tzinfo=timezone.utc)
    import app.dashboard as dashboard_module

    monkeypatch.setattr(dashboard_module, "utcnow", lambda: now)

    async with AsyncSessionLocal() as session:
        log_done = Log(
            telegram_user_id=USER_ID,
            text="did leetcode and worked on the app",
            created_at=datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc),
        )
        log_old = Log(
            telegram_user_id=USER_ID,
            text="ran this morning",
            created_at=datetime(2026, 6, 16, 10, 0, tzinfo=timezone.utc),
        )
        session.add_all([log_done, log_old])
        await session.flush()
        session.add_all(
            [
                ExtractedFacts(
                    log_id=log_done.id,
                    habits=["leetcode"],
                    adherence="yes",
                    mood="focused",
                    trigger="morning coffee",
                    context="at desk",
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
        session.add(UserProgress(telegram_user_id=USER_ID, xp=120, level=2))
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

    assert dashboard.progress.level == 2
    assert dashboard.progress.xp == 120

    habits = {habit.name: habit for habit in dashboard.habits}
    assert habits["leetcode"].today_status == "done"
    assert habits["read"].today_status == "missing"
    assert habits["gym"].today_status == "not_due"

    assert dashboard.recent_logs[0].text == "did leetcode and worked on the app"
    assert dashboard.recent_logs[0].habits == ["leetcode"]
    assert dashboard.recent_interventions[0].kind == "proactive"
