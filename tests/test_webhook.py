from unittest.mock import AsyncMock

from httpx import AsyncClient
from sqlalchemy import func, select

from app.config import settings
from app.db.models import Log
from app.db.session import AsyncSessionLocal
from app.main import app, get_send_message

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
