"""Tests for the proactive agent — milestone 6 acceptance criteria."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.agent.runner import run_tick
from app.config import get_app_timezone
from app.db.models import HabitEvidenceOverride, Intervention
from app.db.session import AsyncSessionLocal
from app.main import app

USER_ID = 12345


def _today_at(hour: int) -> datetime:
    now = datetime.now(get_app_timezone())
    return now.replace(hour=hour, minute=0, second=0, microsecond=0)


def _make_decide_response(
    action: str,
    reason: str,
    technique: str | None = None,
    message: str | None = None,
) -> MagicMock:
    """Build a fake Anthropic response containing a decide_intervention tool call."""
    block = MagicMock()
    block.type = "tool_use"
    block.name = "decide_intervention"
    block.input = {
        "action": action,
        "reason": reason,
        "technique": technique,
        "message": message,
    }
    resp = MagicMock()
    resp.content = [block]
    return resp


# ---------------------------------------------------------------------------
# AC1: drifting fixture → produces a proactive intervention row, sends message
# ---------------------------------------------------------------------------


async def test_tick_drifting_sends_proactive(db_session, monkeypatch) -> None:
    """A drifting user gets a proactive nudge and an interventions row."""
    mock_complete = AsyncMock(
        return_value=_make_decide_response(
            action="respond",
            reason="User has missed gym 3 days in a row",
            technique="implementation intentions",
            message="Try scheduling your gym session as a fixed appointment.",
        )
    )
    monkeypatch.setattr("app.agent.graph.complete", mock_complete)

    mock_send = AsyncMock()
    monkeypatch.setattr("app.agent.runner.send_message", mock_send)

    # Patch memory and RAG to return canned data (avoids real I/O)
    monkeypatch.setattr(
        "app.agent.tools._recall_history", lambda q, uid, limit=5: "missed gym 3 days"
    )
    monkeypatch.setattr("app.agent.tools._retrieve", AsyncMock(return_value=[]))

    await run_tick(USER_ID, now=_today_at(13))

    # intervention row written
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Intervention).where(Intervention.telegram_user_id == USER_ID)
        )
        rows = result.scalars().all()

    assert len(rows) == 1
    row = rows[0]
    assert row.kind == "proactive"
    assert row.reason == "User has missed gym 3 days in a row"
    assert row.technique == "implementation intentions"
    assert row.message is not None

    # send_message was called
    mock_send.assert_awaited_once()


# ---------------------------------------------------------------------------
# AC2: doing-fine fixture → silence row, no send
# ---------------------------------------------------------------------------


async def test_tick_doing_fine_stays_silent(db_session, monkeypatch) -> None:
    """A user on track triggers a silence decision with no Telegram message sent."""
    mock_complete = AsyncMock(
        return_value=_make_decide_response(
            action="silent",
            reason="User completed all habits today",
        )
    )
    monkeypatch.setattr("app.agent.graph.complete", mock_complete)

    mock_send = AsyncMock()
    monkeypatch.setattr("app.agent.runner.send_message", mock_send)

    monkeypatch.setattr(
        "app.agent.tools._recall_history",
        lambda q, uid, limit=5: "completed gym, meditation",
    )
    monkeypatch.setattr("app.agent.tools._retrieve", AsyncMock(return_value=[]))

    await run_tick(USER_ID, now=_today_at(13))

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Intervention).where(Intervention.telegram_user_id == USER_ID)
        )
        rows = result.scalars().all()

    assert len(rows) == 1
    assert rows[0].kind == "silence"
    assert "completed all habits" in rows[0].reason

    # send_message must NOT have been called
    mock_send.assert_not_awaited()


# ---------------------------------------------------------------------------
# AC0: due habit with no evidence after the window → one fallback check-in
# ---------------------------------------------------------------------------


async def test_tick_due_habit_sends_one_fallback_checkin(db_session, monkeypatch) -> None:
    mock_complete = AsyncMock()
    monkeypatch.setattr("app.agent.graph.complete", mock_complete)
    monkeypatch.setattr("app.agent.tools._recall_history", lambda q, uid, limit=5: "")

    mock_send = AsyncMock()
    monkeypatch.setattr("app.agent.runner.send_message", mock_send)

    await run_tick(USER_ID, now=_today_at(21))

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Intervention).where(Intervention.telegram_user_id == USER_ID)
        )
        rows = result.scalars().all()

    assert len(rows) == 1
    assert rows[0].kind == "check-in"
    assert "missing evidence" in rows[0].reason
    assert rows[0].message is not None
    assert "Quick check-in" in rows[0].message
    mock_send.assert_awaited_once()
    mock_complete.assert_not_awaited()

    mock_complete.return_value = _make_decide_response(
        action="silent",
        reason="already asked for a check-in",
    )
    mock_send.reset_mock()

    await run_tick(USER_ID, now=_today_at(21))

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Intervention).where(
                Intervention.telegram_user_id == USER_ID,
                Intervention.kind == "check-in",
            )
        )
        checkins = result.scalars().all()

    assert len(checkins) == 1
    mock_send.assert_not_awaited()


# ---------------------------------------------------------------------------
# AC3: daily cap — fifth tick is blocked without calling LLM
# ---------------------------------------------------------------------------


async def test_daily_cap_blocks_fifth_tick(db_session, monkeypatch) -> None:
    """Pre-insert four proactive rows; a fifth tick must write silence without hitting the LLM."""
    # Pre-seed four proactive interventions for today
    async with AsyncSessionLocal() as session:
        for _ in range(4):
            session.add(
                Intervention(
                    telegram_user_id=USER_ID,
                    kind="proactive",
                    reason="sent earlier today",
                    technique="habit stacking",
                    message="Stack your workout with your morning coffee.",
                )
            )
        await session.commit()

    mock_complete = AsyncMock()
    monkeypatch.setattr("app.agent.graph.complete", mock_complete)

    mock_send = AsyncMock()
    monkeypatch.setattr("app.agent.runner.send_message", mock_send)

    await run_tick(USER_ID)

    # LLM must not have been called
    mock_complete.assert_not_awaited()

    # A silence row with "daily cap reached" must exist
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Intervention).where(
                Intervention.telegram_user_id == USER_ID,
                Intervention.kind == "silence",
            )
        )
        rows = result.scalars().all()

    assert len(rows) == 1
    assert rows[0].reason == "daily cap reached"

    mock_send.assert_not_awaited()


async def test_tick_prompt_uses_corrected_habit_state(db_session, monkeypatch) -> None:
    captured: dict[str, str] = {}

    async with AsyncSessionLocal() as session:
        session.add(
            HabitEvidenceOverride(
                telegram_user_id=USER_ID,
                log_id=None,
                habit_name="read",
                target_date=_today_at(13).date(),
                override_status="yes",
                user_text="count that as reading",
                reason="test correction",
            )
        )
        await session.commit()

    async def _capture_complete(*args, **kwargs):
        captured["content"] = kwargs["messages"][0]["content"]
        return _make_decide_response(
            action="silent",
            reason="User completed a corrected habit already",
        )

    monkeypatch.setattr("app.agent.graph.complete", _capture_complete)
    monkeypatch.setattr("app.agent.tools._recall_history", lambda q, uid, limit=5: "")
    monkeypatch.setattr("app.agent.tools._retrieve", AsyncMock(return_value=[]))
    monkeypatch.setattr("app.agent.runner.send_message", AsyncMock())

    await run_tick(USER_ID, now=_today_at(13))

    assert "read: done corrected" in captured["content"]


async def test_tick_prompt_uses_checkin_answered_missed_state(db_session, monkeypatch) -> None:
    captured: dict[str, str] = {}

    async with AsyncSessionLocal() as session:
        session.add(
            HabitEvidenceOverride(
                telegram_user_id=USER_ID,
                log_id=None,
                habit_name="read",
                target_date=_today_at(13).date(),
                override_status="no",
                user_text="no",
                reason="check-in answer for intervention 1",
            )
        )
        await session.commit()

    async def _capture_complete(*args, **kwargs):
        captured["content"] = kwargs["messages"][0]["content"]
        return _make_decide_response(
            action="silent",
            reason="User answered the read check-in as missed",
        )

    monkeypatch.setattr("app.agent.graph.complete", _capture_complete)
    monkeypatch.setattr("app.agent.tools._recall_history", lambda q, uid, limit=5: "")
    monkeypatch.setattr("app.agent.tools._retrieve", AsyncMock(return_value=[]))
    monkeypatch.setattr("app.agent.runner.send_message", AsyncMock())

    await run_tick(USER_ID, now=_today_at(13))

    assert "read: missing corrected" in captured["content"]


def test_proactive_lesson_query_uses_state_and_recent_pattern() -> None:
    from app.agent.graph import build_proactive_lesson_query

    query = build_proactive_lesson_query(
        habit_state_summary="- gym: missing\n- read: done",
        history="missed gym after late work twice this week",
    )

    assert query is not None
    assert "gym: missing" in query
    assert "missed gym after late work" in query
    assert "behavior change habit" not in query


async def test_tick_retrieves_lessons_from_concrete_state(db_session, monkeypatch) -> None:
    captured: dict[str, str] = {}

    lesson = MagicMock()
    lesson.content = (
        "technique: implementation intentions\n"
        "lesson: choose the exact prompt before the next workday starts."
    )

    async def _capture_retrieve(query: str, top_k: int = 5, top_n: int = 3):
        captured["query"] = query
        return [lesson]

    async def _capture_complete(*args, **kwargs):
        captured["content"] = kwargs["messages"][0]["content"]
        return _make_decide_response(
            action="respond",
            reason="recent late-work gym drift fits implementation intentions",
            technique="implementation intentions",
            message="Use implementation intentions: after closing your laptop, change for gym.",
        )

    monkeypatch.setattr("app.agent.graph.complete", _capture_complete)
    monkeypatch.setattr(
        "app.agent.tools._recall_history",
        lambda q, uid, limit=5: "missed gym after late work twice this week",
    )
    monkeypatch.setattr("app.agent.tools._retrieve", _capture_retrieve)
    monkeypatch.setattr("app.agent.runner.send_message", AsyncMock())

    await run_tick(USER_ID, now=_today_at(13))

    assert "missed gym after late work" in captured["query"]
    assert "behavior change habit" not in captured["query"]
    assert "Relevant self-authored lessons" in captured["content"]
    assert "implementation intentions" in captured["content"]


# ---------------------------------------------------------------------------
# AC4: /scheduler/tick endpoint rejects requests without the correct secret
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scheduler_tick_endpoint_rejects_without_secret(monkeypatch) -> None:
    """POST /scheduler/tick with no secret or wrong secret must return 403."""
    from app import config

    monkeypatch.setattr(config.settings, "scheduler_secret", "correct-secret")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        # No secret at all
        resp_no_secret = await c.post("/scheduler/tick")
        assert resp_no_secret.status_code == 403

        # Wrong secret
        resp_wrong = await c.post("/scheduler/tick?secret=wrong")
        assert resp_wrong.status_code == 403
