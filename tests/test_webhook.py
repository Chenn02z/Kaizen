from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.config import settings
from app.dashboard import DashboardData
from app.db.models import ExtractedFacts, HabitEvidenceOverride, Log, UserProgress
from app.db.session import AsyncSessionLocal
from app.main import app, get_send_message
from app.telegram.webapp import dashboard_inline_keyboard

VALID_HEADERS = {"X-Telegram-Bot-Api-Secret-Token": settings.telegram_webhook_secret}

ALLOWED_UID = settings.allowed_user_id
OTHER_UID = ALLOWED_UID + 1


def _make_update(user_id: int, text: str = "hello") -> dict:
    return {
        "update_id": 1,
        "message": {
            "message_id": 42,
            "from": {"id": user_id},
            "chat": {"id": user_id},
            "text": text,
        },
    }


async def _log_count() -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count()).select_from(Log))
        return result.scalar_one()


async def _override_count() -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count()).select_from(HabitEvidenceOverride))
        return result.scalar_one()


# ---------------------------------------------------------------------------
# AC1 + AC2: allowed user → row inserted, send_message called
# ---------------------------------------------------------------------------


async def test_allowed_user_inserts_row_and_echoes(client: AsyncClient, db_session) -> None:
    mock_send = AsyncMock()
    app.dependency_overrides[get_send_message] = lambda: mock_send

    try:
        response = await client.post(
            "/webhook",
            json=_make_update(ALLOWED_UID, text="hello kaizen"),
            headers=VALID_HEADERS,
        )
    finally:
        app.dependency_overrides.pop(get_send_message, None)

    assert response.status_code == 200
    count = await _log_count()
    assert count == 1, f"Expected 1 log row, got {count}"

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Log))
        row = result.scalar_one()
    assert row.text == "hello kaizen"
    assert row.telegram_user_id == ALLOWED_UID

    mock_send.assert_called_once_with(chat_id=ALLOWED_UID, text="hello kaizen")


# ---------------------------------------------------------------------------
# AC3: disallowed user → 200, no row, no echo
# ---------------------------------------------------------------------------


async def test_disallowed_user_returns_200_no_row(client: AsyncClient, db_session) -> None:
    mock_send = AsyncMock()
    app.dependency_overrides[get_send_message] = lambda: mock_send

    try:
        response = await client.post(
            "/webhook",
            json=_make_update(OTHER_UID),
            headers=VALID_HEADERS,
        )
    finally:
        app.dependency_overrides.pop(get_send_message, None)

    assert response.status_code == 200
    assert await _log_count() == 0
    mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# Missing/wrong secret → 403, no row, no echo
# ---------------------------------------------------------------------------


async def test_wrong_secret_returns_403(client: AsyncClient, db_session) -> None:
    mock_send = AsyncMock()
    app.dependency_overrides[get_send_message] = lambda: mock_send

    try:
        # No secret header at all
        response_no_header = await client.post(
            "/webhook",
            json=_make_update(ALLOWED_UID),
        )
        # Wrong secret header
        response_wrong = await client.post(
            "/webhook",
            json=_make_update(ALLOWED_UID),
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong_secret"},
        )
    finally:
        app.dependency_overrides.pop(get_send_message, None)

    assert response_no_header.status_code == 403
    assert response_wrong.status_code == 403
    assert await _log_count() == 0
    mock_send.assert_not_called()


async def test_reflection_query_uses_reflection_path(
    client: AsyncClient,
    db_session,
    monkeypatch,
) -> None:
    mock_send = AsyncMock()
    app.dependency_overrides[get_send_message] = lambda: mock_send

    mock_reflection = AsyncMock(return_value="You usually slip after stressful work days.")
    mock_agent = AsyncMock(return_value="agent reply")
    monkeypatch.setattr("app.main._answer_reflection", mock_reflection)
    monkeypatch.setattr("app.main.run_user_message", mock_agent)

    try:
        response = await client.post(
            "/webhook",
            json=_make_update(ALLOWED_UID, text="how was my week?"),
            headers=VALID_HEADERS,
        )
    finally:
        app.dependency_overrides.pop(get_send_message, None)

    assert response.status_code == 200
    mock_reflection.assert_awaited_once_with("how was my week?", ALLOWED_UID)
    mock_agent.assert_not_awaited()
    mock_send.assert_called_once_with(
        chat_id=ALLOWED_UID,
        text="You usually slip after stressful work days.",
    )


@pytest.mark.asyncio
async def test_dashboard_command_launches_webapp_and_skips_log(
    client: AsyncClient,
    db_session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "public_url", "https://example.com")
    mock_send = AsyncMock()
    app.dependency_overrides[get_send_message] = lambda: mock_send

    try:
        response = await client.post(
            "/webhook",
            json=_make_update(ALLOWED_UID, text="/dashboard"),
            headers=VALID_HEADERS,
        )
    finally:
        app.dependency_overrides.pop(get_send_message, None)

    assert response.status_code == 200
    assert await _log_count() == 0
    mock_send.assert_awaited_once_with(
        chat_id=ALLOWED_UID,
        text="Open your dashboard:",
        reply_markup=dashboard_inline_keyboard(),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["/start", "/app"])
async def test_dashboard_alias_commands_launch_webapp_and_skip_log(
    client: AsyncClient,
    db_session,
    monkeypatch,
    command: str,
) -> None:
    monkeypatch.setattr(settings, "public_url", "https://example.com")
    mock_send = AsyncMock()
    app.dependency_overrides[get_send_message] = lambda: mock_send

    try:
        response = await client.post(
            "/webhook",
            json=_make_update(ALLOWED_UID, text=command),
            headers=VALID_HEADERS,
        )
    finally:
        app.dependency_overrides.pop(get_send_message, None)

    assert response.status_code == 200
    assert await _log_count() == 0
    mock_send.assert_awaited_once_with(
        chat_id=ALLOWED_UID,
        text="Open your dashboard:",
        reply_markup=dashboard_inline_keyboard(),
    )


async def test_false_negative_correction_updates_dashboard_and_keeps_audit_rows(
    client: AsyncClient,
    db_session,
    monkeypatch,
) -> None:
    import app.dashboard as dashboard_module

    now = datetime(2026, 6, 21, 21, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(dashboard_module, "utcnow", lambda: now)

    async with AsyncSessionLocal() as session:
        log = Log(
            telegram_user_id=ALLOWED_UID,
            text="worked out hard after lunch",
            created_at=datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc),
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
        await session.commit()

    params = {"secret": settings.miniapp_secret} if settings.miniapp_secret else None
    before = DashboardData.model_validate((await client.get("/dashboard", params=params)).json())
    before_habits = {habit.name: habit for habit in before.habits}
    assert before_habits["gym"].today_status == "missing"

    mock_send = AsyncMock()
    app.dependency_overrides[get_send_message] = lambda: mock_send
    try:
        response = await client.post(
            "/webhook",
            json=_make_update(ALLOWED_UID, text="count that as gym"),
            headers=VALID_HEADERS,
        )
    finally:
        app.dependency_overrides.pop(get_send_message, None)

    assert response.status_code == 200
    assert await _log_count() == 1
    assert await _override_count() == 1
    mock_send.assert_awaited_once()

    after = DashboardData.model_validate((await client.get("/dashboard", params=params)).json())
    after_habits = {habit.name: habit for habit in after.habits}
    assert after_habits["gym"].today_status == "done"
    assert after_habits["gym"].is_corrected_today is True

    async with AsyncSessionLocal() as session:
        facts = (await session.execute(select(ExtractedFacts))).scalar_one()
        override = (await session.execute(select(HabitEvidenceOverride))).scalar_one()
    assert facts.habits == []
    assert override.habit_name == "gym"


async def test_false_positive_correction_removes_completion_credit(
    client: AsyncClient,
    db_session,
    monkeypatch,
) -> None:
    import app.dashboard as dashboard_module

    now = datetime(2026, 6, 21, 21, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(dashboard_module, "utcnow", lambda: now)

    async with AsyncSessionLocal() as session:
        log = Log(
            telegram_user_id=ALLOWED_UID,
            text="great workout today",
            created_at=datetime(2026, 6, 21, 8, 0, tzinfo=timezone.utc),
        )
        session.add(log)
        await session.flush()
        session.add(
            ExtractedFacts(
                log_id=log.id,
                habits=["gym"],
                adherence="yes",
            )
        )
        await session.commit()

    mock_send = AsyncMock()
    app.dependency_overrides[get_send_message] = lambda: mock_send
    try:
        response = await client.post(
            "/webhook",
            json=_make_update(ALLOWED_UID, text="that was not a workout"),
            headers=VALID_HEADERS,
        )
    finally:
        app.dependency_overrides.pop(get_send_message, None)

    assert response.status_code == 200
    assert await _override_count() == 1
    params = {"secret": settings.miniapp_secret} if settings.miniapp_secret else None
    after = DashboardData.model_validate((await client.get("/dashboard", params=params)).json())
    after_habits = {habit.name: habit for habit in after.habits}
    assert after_habits["gym"].today_status == "missing"


async def test_ambiguous_correction_asks_follow_up_and_skips_override(
    client: AsyncClient,
    db_session,
) -> None:
    async with AsyncSessionLocal() as session:
        log = Log(
            telegram_user_id=ALLOWED_UID,
            text="did both run and gym",
        )
        session.add(log)
        await session.flush()
        session.add(
            ExtractedFacts(
                log_id=log.id,
                habits=["run", "gym"],
                adherence="yes",
            )
        )
        await session.commit()

    mock_send = AsyncMock()
    app.dependency_overrides[get_send_message] = lambda: mock_send
    try:
        response = await client.post(
            "/webhook",
            json=_make_update(ALLOWED_UID, text="do not use that as evidence next time"),
            headers=VALID_HEADERS,
        )
    finally:
        app.dependency_overrides.pop(get_send_message, None)

    assert response.status_code == 200
    assert await _override_count() == 0
    assert await _log_count() == 1
    sent_text = mock_send.await_args.kwargs["text"]
    assert "Which habit should I correct?" in sent_text


async def test_retrying_same_correction_keeps_progress_idempotent(
    client: AsyncClient,
    db_session,
) -> None:
    async with AsyncSessionLocal() as session:
        log = Log(
            telegram_user_id=ALLOWED_UID,
            text="worked out hard after lunch",
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
        await session.commit()

    for _ in range(2):
        mock_send = AsyncMock()
        app.dependency_overrides[get_send_message] = lambda: mock_send
        try:
            response = await client.post(
                "/webhook",
                json=_make_update(ALLOWED_UID, text="count that as gym"),
                headers=VALID_HEADERS,
            )
        finally:
            app.dependency_overrides.pop(get_send_message, None)
        assert response.status_code == 200

    async with AsyncSessionLocal() as session:
        progress = (
            await session.execute(
                select(UserProgress).where(UserProgress.telegram_user_id == ALLOWED_UID)
            )
        ).scalar_one()
        overrides = (
            await session.execute(
                select(HabitEvidenceOverride).where(
                    HabitEvidenceOverride.telegram_user_id == ALLOWED_UID
                )
            )
        ).scalars().all()

    assert progress.xp == 50
    assert progress.level == 1
    assert len(overrides) == 2
