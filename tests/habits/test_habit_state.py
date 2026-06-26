from datetime import datetime, timezone

from app.db.models import ExtractedFacts, HabitEvidenceOverride, Log
from app.db.session import AsyncSessionLocal
from app.habits.plan import HabitPlanContext
from app.habits.state import get_habit_day_states

USER_ID = 12345


def _plan(
    habit_name: str,
    *,
    cadence_type: str = "daily",
    cadence_value: object | None = None,
    expected_evidence_window: str | None = "20:00",
) -> HabitPlanContext:
    return HabitPlanContext(
        category_name="TEST",
        habit_name=habit_name,
        direction="build",
        cadence_type=cadence_type,
        cadence_value=cadence_value,
        success_condition=f"Completed {habit_name}",
        habit_aliases=[],
        known_triggers=[],
        expected_evidence_window=expected_evidence_window,
    )


async def test_read_model_counts_log_evidence_as_done(db_session) -> None:
    now = datetime(2026, 6, 17, 13, 0, tzinfo=timezone.utc)
    async with AsyncSessionLocal() as session:
        log = Log(
            telegram_user_id=USER_ID,
            text="did leetcode",
            created_at=datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc),
        )
        session.add(log)
        await session.flush()
        session.add(ExtractedFacts(log_id=log.id, habits=["leetcode"], adherence="yes"))
        await session.commit()

    async with AsyncSessionLocal() as session:
        states = await get_habit_day_states(session, USER_ID, [_plan("leetcode")], now)

    state = states[0]
    assert state.day_status == "done"
    assert state.agent_status == "done"
    assert state.weekly_positive_count == 1
    assert state.fallback_checkin_due is False


async def test_read_model_applies_negative_correction_override(db_session) -> None:
    now = datetime(2026, 6, 17, 13, 0, tzinfo=timezone.utc)
    async with AsyncSessionLocal() as session:
        log = Log(
            telegram_user_id=USER_ID,
            text="did leetcode",
            created_at=datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc),
        )
        session.add(log)
        await session.flush()
        session.add(ExtractedFacts(log_id=log.id, habits=["leetcode"], adherence="yes"))
        session.add(
            HabitEvidenceOverride(
                telegram_user_id=USER_ID,
                log_id=log.id,
                habit_name="leetcode",
                target_date=now.date(),
                override_status="no",
                user_text="that was not leetcode",
                reason="test correction",
            )
        )
        await session.commit()

    async with AsyncSessionLocal() as session:
        states = await get_habit_day_states(session, USER_ID, [_plan("leetcode")], now)

    state = states[0]
    assert state.day_status == "missing"
    assert state.agent_status == "missing"
    assert state.is_corrected is True
    assert state.fallback_checkin_due is True


async def test_read_model_treats_checkin_no_as_answered_not_repeat_due(db_session) -> None:
    now = datetime(2026, 6, 17, 13, 0, tzinfo=timezone.utc)
    async with AsyncSessionLocal() as session:
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
        states = await get_habit_day_states(session, USER_ID, [_plan("read")], now)

    state = states[0]
    assert state.day_status == "missing"
    assert state.is_checkin_answer is True
    assert state.fallback_checkin_due is False


async def test_read_model_counts_partial_checkin_answer_as_done(db_session) -> None:
    now = datetime(2026, 6, 17, 13, 0, tzinfo=timezone.utc)
    async with AsyncSessionLocal() as session:
        session.add(
            HabitEvidenceOverride(
                telegram_user_id=USER_ID,
                log_id=None,
                habit_name="read",
                target_date=now.date(),
                override_status="partial",
                user_text="partial",
                reason="check-in answer for intervention 1",
            )
        )
        await session.commit()

    async with AsyncSessionLocal() as session:
        states = await get_habit_day_states(session, USER_ID, [_plan("read")], now)

    state = states[0]
    assert state.day_status == "done"
    assert state.weekly_positive_count == 1
    assert state.is_checkin_answer is True


async def test_read_model_evaluates_daily_and_specific_weekday_cadence(db_session) -> None:
    wednesday = datetime(2026, 6, 17, 13, 0, tzinfo=timezone.utc)
    thursday = datetime(2026, 6, 18, 13, 0, tzinfo=timezone.utc)
    weekday_plan = _plan(
        "therapy exercises",
        cadence_type="specific_weekdays",
        cadence_value=["wed"],
    )

    async with AsyncSessionLocal() as session:
        states = await get_habit_day_states(
            session,
            USER_ID,
            [_plan("read"), weekday_plan],
            wednesday,
        )

    by_name = {state.habit_name: state for state in states}
    assert by_name["read"].day_status == "missing"
    assert by_name["therapy exercises"].day_status == "missing"

    async with AsyncSessionLocal() as session:
        states = await get_habit_day_states(session, USER_ID, [weekday_plan], thursday)

    assert states[0].day_status == "not_due"


async def test_read_model_uses_weekly_counts_for_times_per_week_cadence(db_session) -> None:
    now = datetime(2026, 6, 21, 13, 0, tzinfo=timezone.utc)
    async with AsyncSessionLocal() as session:
        for created_at in (
            datetime(2026, 6, 16, 10, 0, tzinfo=timezone.utc),
            datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
        ):
            log = Log(telegram_user_id=USER_ID, text="went for a run", created_at=created_at)
            session.add(log)
            await session.flush()
            session.add(ExtractedFacts(log_id=log.id, habits=["run"], adherence="yes"))
        await session.commit()

    async with AsyncSessionLocal() as session:
        states = await get_habit_day_states(
            session,
            USER_ID,
            [_plan("run", cadence_type="times_per_week", cadence_value=3)],
            now,
        )

    state = states[0]
    assert state.weekly_positive_count == 2
    assert state.day_status == "missing"
    assert state.due_reason == "weekly target needs completion today (2/3 done)"
