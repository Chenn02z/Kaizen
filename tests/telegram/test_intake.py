from datetime import date
from unittest.mock import AsyncMock

from sqlalchemy import func, select

from app.dashboard import get_dashboard_data
from app.db.models import (
    HabitCategory,
    HabitCommandFlow,
    HabitEvidenceOverride,
    HabitPlan,
    HabitProgress,
    Log,
)
from app.db.session import AsyncSessionLocal
from app.extract.schema import ExtractedFacts
from app.habits.plan import get_habit_plan_context, render_habit_plan_for_prompt
from app.telegram.intake import TelegramIntakeMessage, handle_message

ALLOWED_UID = 123456789


def _message(text: str) -> TelegramIntakeMessage:
    return TelegramIntakeMessage(
        telegram_user_id=ALLOWED_UID,
        chat_id=ALLOWED_UID,
        text=text,
    )


async def _log_count() -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count()).select_from(Log))
        return result.scalar_one()


async def _flow_count() -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count()).select_from(HabitCommandFlow))
        return result.scalar_one()


async def test_habits_command_returns_plan_summary_without_log(db_session) -> None:
    outcome = await handle_message(_message("/habits@KaizenBot"))

    assert outcome.handled is True
    assert await _log_count() == 0
    assert len(outcome.replies) == 1
    text = outcome.replies[0].text
    assert "FITNESS" in text
    assert "- gym: 3x/week - Completed a gym workout session" in text
    assert "aliases: gym, lifted, workout, trained chest" in text


async def test_habit_add_happy_path_reuses_existing_category_and_updates_context(
    db_session,
) -> None:
    add_outcome = await handle_message(_message("/habit_add"))
    assert add_outcome.replies[0].text == "Habit name?"

    await handle_message(_message("sleep"))
    await handle_message(_message("self"))
    await handle_message(_message("daily"))
    await handle_message(_message("Slept before midnight"))
    summary = await handle_message(_message("early bedtime, lights out"))
    assert "Confirm this habit? yes/no" in summary.replies[0].text
    saved = await handle_message(_message("yes"))

    assert saved.replies[0].text == "Saved habit 'sleep'."
    assert await _log_count() == 0
    assert await _flow_count() == 0

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(HabitPlan, HabitCategory.name)
            .join(HabitCategory, HabitCategory.id == HabitPlan.category_id)
            .where(HabitPlan.habit_name == "sleep")
        )
        plan, category_name = result.one()
        plans = await get_habit_plan_context(session, ALLOWED_UID)
        dashboard = await get_dashboard_data(ALLOWED_UID, session)

    assert category_name == "SELF"
    assert plan.cadence_type == "daily"
    assert plan.cadence_value is None
    assert plan.success_condition == "Slept before midnight"
    assert plan.habit_aliases == ["early bedtime", "lights out"]
    assert "sleep (SELF, build, daily)" in render_habit_plan_for_prompt(plans)
    assert {habit.name for habit in dashboard.habits} >= {"sleep"}


async def test_habit_add_confirms_new_category_once(db_session) -> None:
    await handle_message(_message("/habit_add"))
    await handle_message(_message("meditate"))
    confirm_category = await handle_message(_message("mind"))

    assert confirm_category.replies[0].text == "Create new category 'MIND'? yes/no"

    await handle_message(_message("yes"))
    await handle_message(_message("weekdays"))
    await handle_message(_message("Meditated for ten minutes"))
    await handle_message(_message("skip"))
    await handle_message(_message("yes"))

    async with AsyncSessionLocal() as session:
        category_count = (
            await session.execute(
                select(func.count())
                .select_from(HabitCategory)
                .where(HabitCategory.name == "MIND")
            )
        ).scalar_one()
        plan = (
            await session.execute(select(HabitPlan).where(HabitPlan.habit_name == "meditate"))
        ).scalar_one()

    assert category_count == 1
    assert plan.cadence_type == "specific_weekdays"
    assert plan.cadence_value == ["mon", "tue", "wed", "thu", "fri"]


async def test_habit_add_invalid_cadence_keeps_partial_plan_unwritten(db_session) -> None:
    await handle_message(_message("/habit_add"))
    await handle_message(_message("meditate"))
    await handle_message(_message("self"))
    invalid = await handle_message(_message("whenever I feel like it"))

    assert "I only support daily" in invalid.replies[0].text
    assert await _log_count() == 0
    assert await _flow_count() == 1
    async with AsyncSessionLocal() as session:
        count = (
            await session.execute(
                select(func.count())
                .select_from(HabitPlan)
                .where(HabitPlan.habit_name == "meditate")
            )
        ).scalar_one()
    assert count == 0


async def test_cancel_during_habit_add_clears_flow_without_plan_or_log(db_session) -> None:
    await handle_message(_message("/habit_add"))
    await handle_message(_message("meditate"))
    canceled = await handle_message(_message("cancel"))

    assert canceled.replies[0].text == "Canceled. No habit-plan changes were saved."
    assert await _log_count() == 0
    assert await _flow_count() == 0
    async with AsyncSessionLocal() as session:
        count = (
            await session.execute(
                select(func.count())
                .select_from(HabitPlan)
                .where(HabitPlan.habit_name == "meditate")
            )
        ).scalar_one()
    assert count == 0


async def test_habit_edit_aliases_update_extraction_context_without_old_fact_mutation(
    db_session,
) -> None:
    started = await handle_message(_message("/habit_edit gym"))
    assert "Editing 'gym'." in started.replies[0].text

    draft = await handle_message(_message("aliases: strength training, lifted heavy"))
    assert "Updated draft. Save it?" in draft.replies[0].text
    saved = await handle_message(_message("yes"))

    assert saved.replies[0].text == "Saved updates for 'gym'."
    assert await _log_count() == 0

    async with AsyncSessionLocal() as session:
        plan = (
            await session.execute(select(HabitPlan).where(HabitPlan.habit_name == "gym"))
        ).scalar_one()
        plans = await get_habit_plan_context(session, ALLOWED_UID)

    assert plan.habit_aliases == ["strength training", "lifted heavy"]
    prompt = render_habit_plan_for_prompt(plans)
    assert "Aliases/examples: strength training, lifted heavy." in prompt


async def test_habit_edit_duplicate_name_is_rejected_without_saving(db_session) -> None:
    await handle_message(_message("/habit_edit gym"))
    rejected = await handle_message(_message("name: read"))

    assert "'read' already exists" in rejected.replies[0].text
    assert await _flow_count() == 1

    discarded = await handle_message(_message("no"))
    assert discarded.replies[0].text == "No habit changes were saved."

    async with AsyncSessionLocal() as session:
        names = (await session.execute(select(HabitPlan.habit_name))).scalars().all()

    assert "gym" in names
    assert names.count("read") == 1


async def test_habit_edit_rename_updates_progress_and_override_references(db_session) -> None:
    async with AsyncSessionLocal() as session:
        await get_habit_plan_context(session, ALLOWED_UID)
        session.add(HabitProgress(telegram_user_id=ALLOWED_UID, habit_name="gym", xp=50, level=1))
        session.add(
            HabitEvidenceOverride(
                telegram_user_id=ALLOWED_UID,
                log_id=None,
                habit_name="gym",
                target_date=date(2026, 6, 27),
                override_status="yes",
                user_text="yes",
                reason="test override",
            )
        )
        await session.commit()

    await handle_message(_message("/habit_edit gym"))
    await handle_message(_message("name: lifting"))
    saved = await handle_message(_message("yes"))

    assert saved.replies[0].text == "Saved updates for 'lifting'."

    async with AsyncSessionLocal() as session:
        plan = (
            await session.execute(select(HabitPlan).where(HabitPlan.habit_name == "lifting"))
        ).scalar_one()
        progress = (
            await session.execute(
                select(HabitProgress).where(HabitProgress.telegram_user_id == ALLOWED_UID)
            )
        ).scalar_one()
        override = (
            await session.execute(
                select(HabitEvidenceOverride).where(
                    HabitEvidenceOverride.telegram_user_id == ALLOWED_UID
                )
            )
        ).scalar_one()

    assert plan.habit_name == "lifting"
    assert progress.habit_name == "lifting"
    assert override.habit_name == "lifting"


async def test_habit_edit_ambiguous_alias_asks_follow_up_without_change(db_session) -> None:
    async with AsyncSessionLocal() as session:
        await get_habit_plan_context(session, ALLOWED_UID)
        category = (
            await session.execute(select(HabitCategory).where(HabitCategory.name == "FITNESS"))
        ).scalar_one()
        session.add(
            HabitPlan(
                telegram_user_id=ALLOWED_UID,
                category_id=category.id,
                habit_name="yoga",
                direction="build",
                cadence_type="times_per_week",
                cadence_value=2,
                success_condition="Completed a yoga session",
                habit_aliases=["workout"],
                known_triggers=[],
                fallback_checkin_enabled=True,
                expected_evidence_window="20:00",
            )
        )
        await session.commit()

    outcome = await handle_message(_message("/habit_edit workout"))

    assert "I found multiple matching habits" in outcome.replies[0].text
    assert "gym" in outcome.replies[0].text
    assert "yoga" in outcome.replies[0].text
    assert await _log_count() == 0

    async with AsyncSessionLocal() as session:
        gym = (
            await session.execute(select(HabitPlan).where(HabitPlan.habit_name == "gym"))
        ).scalar_one()
        yoga = (
            await session.execute(select(HabitPlan).where(HabitPlan.habit_name == "yoga"))
        ).scalar_one()

    assert gym.success_condition == "Completed a gym workout session"
    assert yoga.success_condition == "Completed a yoga session"


async def test_unsupported_command_replies_without_mutation(db_session) -> None:
    outcome = await handle_message(_message("/habit_delete gym"))

    assert outcome.handled is True
    assert await _log_count() == 0
    assert "I don't support /habit_delete yet." in outcome.replies[0].text


async def test_ordinary_log_persists_and_returns_agent_reply(db_session, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.telegram.intake.extract",
        AsyncMock(return_value=ExtractedFacts(habits=[], adherence=None)),
    )
    monkeypatch.setattr("app.telegram.intake.store_facts", lambda *args: None)
    monkeypatch.setattr("app.telegram.intake.run_user_message", AsyncMock(return_value="logged"))

    outcome = await handle_message(_message("read before bed"))

    assert await _log_count() == 1
    assert outcome.replies[0].text == "logged"
