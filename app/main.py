import logging
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from secrets import compare_digest
from typing import Annotated, Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.agent.scheduler import start_scheduler, stop_scheduler
from app.config import settings
from app.telegram.client import send_message, set_webhook
from app.telegram.intake import TelegramIntakeMessage, handle_message

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    if settings.public_url:
        try:
            await set_webhook(f"{settings.public_url}/webhook", settings.telegram_webhook_secret)
        except httpx.HTTPError:
            logger.exception("setWebhook failed; Telegram updates will not arrive")
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Kaizen", lifespan=lifespan)


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


@app.post("/scheduler/tick")
async def scheduler_tick(
    x_scheduler_secret: Annotated[Optional[str], Header()] = None,
) -> dict[str, str]:
    """Debug endpoint: trigger a single proactive tick on demand."""
    if not settings.scheduler_secret or not compare_digest(
        x_scheduler_secret or "", settings.scheduler_secret
    ):
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.agent.runner import run_tick

    await run_tick(settings.allowed_user_id)
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(
    request: Request,
    _send: SendMessageDep,
    x_telegram_bot_api_secret_token: Annotated[Optional[str], Header()] = None,
) -> dict[str, str]:
    # 1. Verify the webhook secret
    if not compare_digest(x_telegram_bot_api_secret_token or "", settings.telegram_webhook_secret):
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

    outcome = await handle_message(
        TelegramIntakeMessage(
            telegram_user_id=message.from_.id,
            chat_id=message.chat.id,
            text=message.text or "",
        )
    )
    for reply in outcome.replies:
        await _send(chat_id=reply.chat_id, text=reply.text)

    return {}
