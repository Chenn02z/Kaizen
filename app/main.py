import logging
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agent.scheduler import start_scheduler, stop_scheduler
from app.config import settings
from app.dashboard import DashboardData, get_dashboard_data
from app.db.session import AsyncSessionLocal
from app.gamification.stats import UserStats, get_user_stats
from app.telegram.client import send_message
from app.telegram.intake import TelegramIntakeMessage, handle_message
from app.telegram.webapp import dashboard_menu_button

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mini App static bundle (built from webapp/ via `npm run build`)
# ---------------------------------------------------------------------------

_WEBAPP_DIST = Path(__file__).resolve().parent.parent / "webapp" / "dist"


# ---------------------------------------------------------------------------
# Startup: register Telegram menu button
# ---------------------------------------------------------------------------


async def _register_menu_button() -> None:
    """Register the Mini App menu button with Telegram on startup."""
    menu_button = dashboard_menu_button()
    if menu_button is None:
        return
    url = f"https://api.telegram.org/bot{settings.telegram_token}/setChatMenuButton"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json={"menu_button": menu_button},
        )
        if not resp.is_success:
            logger.warning("setChatMenuButton failed: %s %s", resp.status_code, resp.text)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    await _register_menu_button()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Kaizen", lifespan=lifespan)

# Hashed JS/CSS for the Mini App. Mounted only when a build exists so the
# server still starts in environments where webapp/dist hasn't been built.
if (_WEBAPP_DIST / "assets").is_dir():
    app.mount(
        "/miniapp/assets",
        StaticFiles(directory=_WEBAPP_DIST / "assets"),
        name="miniapp-assets",
    )


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


@app.get("/me")
async def me(request: Request) -> UserStats:
    if settings.miniapp_secret and request.query_params.get("secret") != settings.miniapp_secret:
        raise HTTPException(status_code=403, detail="Forbidden")
    async with AsyncSessionLocal() as session:
        return await get_user_stats(settings.allowed_user_id, session)


@app.get("/dashboard", response_model=DashboardData)
async def dashboard(request: Request) -> DashboardData:
    if settings.miniapp_secret and request.query_params.get("secret") != settings.miniapp_secret:
        raise HTTPException(status_code=403, detail="Forbidden")
    async with AsyncSessionLocal() as session:
        return await get_dashboard_data(settings.allowed_user_id, session)


@app.get("/miniapp", response_class=HTMLResponse)
async def miniapp() -> str:
    index = _WEBAPP_DIST / "index.html"
    if not index.is_file():
        raise HTTPException(
            status_code=503,
            detail="Mini App not built. Run `npm run build` in webapp/.",
        )
    return index.read_text(encoding="utf-8").replace(
        "%%MINIAPP_SECRET%%", settings.miniapp_secret
    )


@app.post("/scheduler/tick")
async def scheduler_tick(request: Request) -> dict[str, str]:
    """Debug endpoint: trigger a single proactive tick on demand."""
    secret = request.query_params.get("secret")
    if not settings.scheduler_secret or secret != settings.scheduler_secret:
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

    outcome = await handle_message(
        TelegramIntakeMessage(
            telegram_user_id=message.from_.id,
            chat_id=message.chat.id,
            text=message.text or "",
        )
    )
    for reply in outcome.replies:
        if reply.reply_markup is None:
            await _send(chat_id=reply.chat_id, text=reply.text)
        else:
            await _send(
                chat_id=reply.chat_id,
                text=reply.text,
                reply_markup=reply.reply_markup,
            )

    return {}
