from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.agent.runner import run_user_message
from app.db.models import CorpusChunk, ExtractedFacts, Log
from app.db.session import AsyncSessionLocal

USER_ID = 12345


def _make_text_response(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


def _make_chunk(content: str) -> CorpusChunk:
    chunk = CorpusChunk()
    chunk.filename = "weekly_targets.md"
    chunk.content = content
    chunk.content_hash = "abc"
    chunk.embedding = [0.0] * 1536
    return chunk


async def test_run_user_message_passes_weekly_habit_state_into_reply_prompt(
    db_session,
    monkeypatch,
) -> None:
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

    monkeypatch.setattr(
        "app.agent.tools._retrieve",
        AsyncMock(return_value=[_make_chunk("Implementation intentions: plan the next run slot.")]),
    )
    monkeypatch.setattr(
        "app.agent.tools._recall_history",
        lambda q, uid, limit=5: "logged two runs this week",
    )

    captured: dict[str, str] = {}

    async def fake_complete(messages, *, system=None, max_tokens=1024, tools=None):
        captured["system"] = system or ""
        return _make_text_response("reply")

    monkeypatch.setattr("app.rag.replies.complete", fake_complete)

    reply = await run_user_message(
        telegram_user_id=USER_ID,
        user_text="Do I need to run today?",
        now=datetime(2026, 6, 20, 13, 0, tzinfo=timezone.utc),
    )

    assert reply == "reply"
    assert "Current habit state:" in captured["system"]
    assert "run: not_due." in captured["system"]
    assert "cadence=times_per_week=3" in captured["system"]
    assert "due_today=no" in captured["system"]
    assert "weekly_progress=2/3" in captured["system"]
