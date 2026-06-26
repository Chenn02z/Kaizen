from unittest.mock import AsyncMock

from sqlalchemy import func, select

from app.db.models import Log
from app.db.session import AsyncSessionLocal
from app.extract.schema import ExtractedFacts
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


async def test_habits_command_returns_plan_summary_without_log(db_session) -> None:
    outcome = await handle_message(_message("/habits@KaizenBot"))

    assert outcome.handled is True
    assert await _log_count() == 0
    assert len(outcome.replies) == 1
    text = outcome.replies[0].text
    assert "FITNESS" in text
    assert "- gym: 3x/week - Completed a gym workout session" in text
    assert "aliases: gym, lifted, workout, trained chest" in text


async def test_reserved_habit_plan_commands_skip_ordinary_logs(db_session) -> None:
    add_outcome = await handle_message(_message("/habit_add"))
    edit_outcome = await handle_message(_message("/habit_edit gym"))

    assert await _log_count() == 0
    assert "reserved for the structured onboarding flow" in add_outcome.replies[0].text
    assert "reserved for the structured onboarding flow" in edit_outcome.replies[0].text


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
