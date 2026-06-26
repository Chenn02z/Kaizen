from datetime import datetime, timezone

from app.corrections.service import handle_correction_message
from app.db.models import ExtractedFacts, HabitEvidenceOverride, Log
from app.db.session import AsyncSessionLocal
from app.habits.evidence import build_effective_evidence_ledger
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
    now = datetime(2026, 6, 15, 13, 0, tzinfo=timezone.utc)
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


async def test_effective_evidence_uses_app_local_log_date(db_session) -> None:
    async with AsyncSessionLocal() as session:
        await get_habit_plan_context(session, USER_ID)
        log = Log(
            telegram_user_id=USER_ID,
            text="did leetcode after work",
            created_at=datetime(2026, 6, 23, 17, 42, tzinfo=timezone.utc),
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
        ledger = await build_effective_evidence_ledger(
            session,
            USER_ID,
            start_date=datetime(2026, 6, 24, tzinfo=timezone.utc).date(),
            end_date=datetime(2026, 6, 24, tzinfo=timezone.utc).date(),
        )

    assert "leetcode" in ledger.states_by_date[datetime(2026, 6, 24).date()]


async def test_due_habits_use_app_local_log_date(db_session) -> None:
    now = datetime(2026, 6, 24, 13, 0, tzinfo=timezone.utc)
    async with AsyncSessionLocal() as session:
        await get_habit_plan_context(session, USER_ID)
        log = Log(
            telegram_user_id=USER_ID,
            text="did leetcode after work",
            created_at=datetime(2026, 6, 23, 17, 42, tzinfo=timezone.utc),
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


async def test_corrections_target_app_local_log_date(db_session) -> None:
    async with AsyncSessionLocal() as session:
        await get_habit_plan_context(session, USER_ID)
        log = Log(
            telegram_user_id=USER_ID,
            text="worked on a hard problem",
            created_at=datetime(2026, 6, 23, 17, 42, tzinfo=timezone.utc),
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

        outcome = await handle_correction_message(
            session,
            telegram_user_id=USER_ID,
            text="count that as leetcode",
            now=datetime(2026, 6, 24, 1, 0, tzinfo=timezone.utc),
        )
        await session.commit()

    assert outcome is not None
    assert outcome.applied is True

    async with AsyncSessionLocal() as session:
        ledger = await build_effective_evidence_ledger(
            session,
            USER_ID,
            start_date=datetime(2026, 6, 24).date(),
            end_date=datetime(2026, 6, 24).date(),
        )

    assert "leetcode" in ledger.states_by_date[datetime(2026, 6, 24).date()]


async def test_due_habits_respect_positive_override(db_session) -> None:
    now = datetime(2026, 6, 15, 13, 0, tzinfo=timezone.utc)
    async with AsyncSessionLocal() as session:
        await get_habit_plan_context(session, USER_ID)
        session.add(
            HabitEvidenceOverride(
                telegram_user_id=USER_ID,
                log_id=None,
                habit_name="read",
                target_date=now.date(),
                override_status="yes",
                user_text="count my reading as done",
                reason="test positive override",
            )
        )
        await session.commit()

    async with AsyncSessionLocal() as session:
        due = await due_habits_missing_evidence(session, USER_ID, now)

    names = {habit.habit_name for habit in due}
    assert "read" not in names


async def test_due_habits_respect_negative_override(db_session) -> None:
    now = datetime(2026, 6, 15, 13, 0, tzinfo=timezone.utc)
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
        session.add(
            HabitEvidenceOverride(
                telegram_user_id=USER_ID,
                log_id=log.id,
                habit_name="leetcode",
                target_date=now.date(),
                override_status="no",
                user_text="undo leetcode credit for today",
                reason="test negative override",
            )
        )
        await session.commit()

    async with AsyncSessionLocal() as session:
        due = await due_habits_missing_evidence(session, USER_ID, now)

    names = {habit.habit_name for habit in due}
    assert "leetcode" in names


async def test_due_habits_do_not_repeat_checkin_answered_no(db_session) -> None:
    now = datetime(2026, 6, 15, 13, 0, tzinfo=timezone.utc)
    async with AsyncSessionLocal() as session:
        await get_habit_plan_context(session, USER_ID)
        session.add(
            HabitEvidenceOverride(
                telegram_user_id=USER_ID,
                log_id=None,
                habit_name="read",
                target_date=now.date(),
                override_status="no",
                user_text="no",
                reason="check-in answer for intervention 1",
            )
        )
        await session.commit()

    async with AsyncSessionLocal() as session:
        due = await due_habits_missing_evidence(session, USER_ID, now)

    names = {habit.habit_name for habit in due}
    assert "read" not in names
