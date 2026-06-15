from datetime import datetime, timezone

from app.db.models import ExtractedFacts, Log
from app.db.session import AsyncSessionLocal
from app.habits.plan import due_habits_missing_evidence, get_habit_plan_context

USER_ID = 12345


async def test_default_habit_plan_is_seeded(db_session) -> None:
    async with AsyncSessionLocal() as session:
        plans = await get_habit_plan_context(session, USER_ID)
        await session.commit()

    assert {plan.habit_name for plan in plans} == {
        "run",
        "gym",
        "leetcode",
        "personal project",
        "read",
    }
    read = next(plan for plan in plans if plan.habit_name == "read")
    assert read.category_name == "SELF"
    assert read.cadence_type == "daily"
    assert read.success_condition == "Completed a real reading session"


async def test_due_habits_use_cadence_and_today_evidence(db_session) -> None:
    now = datetime(2026, 6, 15, 21, 0, tzinfo=timezone.utc)
    async with AsyncSessionLocal() as session:
        await get_habit_plan_context(session, USER_ID)
        log = Log(
            telegram_user_id=USER_ID,
            text="did leetcode",
            created_at=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
        )
        session.add(log)
        await session.flush()
        session.add(
            ExtractedFacts(
                log_id=log.id,
                habits=["leetcode"],
                adherence="yes",
            )
        )
        await session.commit()

    async with AsyncSessionLocal() as session:
        due = await due_habits_missing_evidence(session, USER_ID, now)

    names = {habit.habit_name for habit in due}
    assert "leetcode" not in names
    assert "read" in names
