from collections.abc import Awaitable, Callable
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import settings
from app.db.models import Log
from app.db.session import AsyncSessionLocal
from app.telegram.client import send_message

app = FastAPI(title="Kaizen")


# ---------------------------------------------------------------------------
# Pydantic models for the Telegram Update payload (only fields we use)
# ---------------------------------------------------------------------------


class TelegramUser(BaseModel):
    id: int


class TelegramChat(BaseModel):
    id: int


class TelegramMessage(BaseModel):
    message_id: int
    from_: TelegramUser = Field(alias="from")
    chat: TelegramChat
    text: Optional[str] = None

    model_config = {"populate_by_name": True}


class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessage] = None


# ---------------------------------------------------------------------------
# Dependency: injectable send_message so tests can override it
# ---------------------------------------------------------------------------


SendMessage = Callable[..., Awaitable[None]]


async def get_send_message() -> SendMessage:
    return send_message


SendMessageDep = Annotated[SendMessage, Depends(get_send_message)]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(
    request: Request,
    _send: SendMessageDep,
    x_telegram_bot_api_secret_token: Annotated[Optional[str], Header()] = None,
) -> dict[str, str]:
    # 1. Verify the webhook secret
    if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=403, detail="Forbidden")

    # 2. Parse the update
    body = await request.json()
    update = TelegramUpdate.model_validate(body)

    # 3. Ignore updates without a message
    if update.message is None:
        return {}

    message = update.message

    # 4. Single-user guard: silently drop messages from anyone else
    if message.from_.id != settings.allowed_user_id:
        return {}

    # 5. Persist the log entry
    async with AsyncSessionLocal() as session:
        log = Log(telegram_user_id=message.from_.id, text=message.text or "")
        session.add(log)
        await session.commit()

    # 6. Echo the message back
    await _send(chat_id=message.chat.id, text=message.text or "")

    return {}
