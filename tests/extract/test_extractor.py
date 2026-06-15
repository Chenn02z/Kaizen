from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.db.models import ExtractedFacts as ExtractedFactsModel
from app.db.session import AsyncSessionLocal
from app.extract.extractor import extract
from app.extract.schema import ExtractedFacts
from app.habits.plan import HabitPlanContext
from app.main import app, get_send_message

EXAMPLES = [
    {
        "log": "Went for a 30 min run this morning. Feeling great!",
        "expected": {"habits": ["exercise"], "adherence": "yes", "mood": "great"},
    },
    {
        "log": "Skipped meditation again today. Work was too stressful.",
        "expected": {"habits": ["meditation"], "adherence": "no", "trigger": "work stress"},
    },
    {
        "log": "Did half my workout — only 20 mins instead of 45. Tired from yesterday.",
        "expected": {"habits": ["exercise"], "adherence": "partial", "mood": "tired"},
    },
    {
        "log": "Journaled for 10 minutes before bed. Also drank 8 glasses of water today.",
        "expected": {"habits": ["journaling", "hydration"], "adherence": "yes"},
    },
    {
        "log": "Couldn't sleep well. Skipped both morning run and reading.",
        "expected": {"habits": ["exercise", "reading"], "adherence": "no", "mood": None},
    },
    {
        "log": "Had a salad for lunch instead of fast food. Small win!",
        "expected": {"habits": ["healthy eating"], "adherence": "yes", "mood": "positive"},
    },
]


def _make_tool_response(input_data: dict) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.name = "extract_facts"
    block.input = input_data
    msg = MagicMock()
    msg.content = [block]
    return msg


def _make_text_response() -> MagicMock:
    block = MagicMock()
    block.type = "text"
    msg = MagicMock()
    msg.content = [block]
    return msg


# AC1: hand-written examples produce valid ExtractedFacts
@pytest.mark.parametrize("example", EXAMPLES)
async def test_extract_examples(example: dict, monkeypatch) -> None:
    mock_complete = AsyncMock(return_value=_make_tool_response(example["expected"]))
    monkeypatch.setattr("app.extract.extractor.complete", mock_complete)

    result = await extract(example["log"])

    mock_complete.assert_called_once()
    assert isinstance(result, ExtractedFacts)
    assert result.habits == example["expected"]["habits"]
    if "adherence" in example["expected"] and example["expected"]["adherence"] is not None:
        assert result.adherence is not None
        assert result.adherence.value == example["expected"]["adherence"]
    if example["expected"].get("mood") is not None:
        assert result.mood == example["expected"]["mood"]
    if example["expected"].get("trigger") is not None:
        assert result.trigger == example["expected"]["trigger"]


# AC3: malformed response raises ValidationError or ValueError
async def test_malformed_response_no_tool_block(monkeypatch) -> None:
    mock_complete = AsyncMock(return_value=_make_text_response())
    monkeypatch.setattr("app.extract.extractor.complete", mock_complete)

    with pytest.raises(ValueError):
        await extract("some log text")


async def test_malformed_response_invalid_adherence(monkeypatch) -> None:
    mock_complete = AsyncMock(
        return_value=_make_tool_response({"habits": ["exercise"], "adherence": "invalid_value"})
    )
    monkeypatch.setattr("app.extract.extractor.complete", mock_complete)

    with pytest.raises(ValidationError):
        await extract("some log text")


async def test_extract_uses_habit_plan_context_and_filters_unknown_habits(monkeypatch) -> None:
    plans = [
        HabitPlanContext(
            category_name="SELF",
            habit_name="read",
            direction="build",
            cadence_type="daily",
            success_condition="Completed a real reading session",
            habit_aliases=["read before bed"],
            known_triggers=[],
        )
    ]
    mock_complete = AsyncMock(
        return_value=_make_tool_response(
            {"habits": ["exercise", "read"], "adherence": "yes", "mood": "good"}
        )
    )
    monkeypatch.setattr("app.extract.extractor.complete", mock_complete)

    result = await extract("read before bed", plans)

    assert result.habits == ["read"]
    system_prompt = mock_complete.call_args.kwargs["system"]
    assert "Use only habit names from the user's habit plan" in system_prompt
    assert "read before bed" in system_prompt


# AC2: each inbound message creates one linked extracted_facts row
async def test_webhook_creates_extracted_facts_row(client, db_session, monkeypatch) -> None:
    from app.config import settings

    mock_complete = AsyncMock(
        return_value=_make_tool_response({"habits": ["run"], "adherence": "yes"})
    )
    monkeypatch.setattr("app.extract.extractor.complete", mock_complete)

    mock_send = AsyncMock()
    app.dependency_overrides[get_send_message] = lambda: mock_send

    try:
        response = await client.post(
            "/webhook",
            json={
                "update_id": 1,
                "message": {
                    "message_id": 1,
                    "from": {"id": settings.allowed_user_id},
                    "chat": {"id": settings.allowed_user_id},
                    "text": "Ran 5k today!",
                },
            },
            headers={"X-Telegram-Bot-Api-Secret-Token": settings.telegram_webhook_secret},
        )
    finally:
        app.dependency_overrides.pop(get_send_message, None)

    assert response.status_code == 200

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ExtractedFactsModel))
        rows = result.scalars().all()

    assert len(rows) == 1
    assert rows[0].habits == ["run"]
    assert rows[0].adherence == "yes"
