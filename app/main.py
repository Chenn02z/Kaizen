import asyncio
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

from app.agent.runner import run_user_message
from app.agent.scheduler import start_scheduler, stop_scheduler
from app.config import settings
from app.dashboard import DashboardData, get_dashboard_data
from app.db.models import ExtractedFacts as ExtractedFactsModel
from app.db.models import Log
from app.db.session import AsyncSessionLocal
from app.extract.extractor import extract
from app.extract.schema import ExtractedFacts
from app.gamification.stats import UserStats, get_user_stats
from app.gamification.xp import XPResult, award_xp
from app.habits.plan import get_habit_plan_context
from app.llm.client import complete
from app.memory.recall import detect_patterns, recall_history
from app.memory.store import store_facts
from app.telegram.client import send_message
from app.telegram.webapp import dashboard_inline_keyboard, dashboard_menu_button

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

    if _is_dashboard_command(message.text):
        reply_markup = dashboard_inline_keyboard()
        if reply_markup is None:
            reply_text = "Kaizen dashboard is not configured yet. Set PUBLIC_URL to your HTTPS deployment."
            await _send(chat_id=message.chat.id, text=reply_text)
        else:
            await _send(chat_id=message.chat.id, text="Open your dashboard:", reply_markup=reply_markup)
        return {}

    # 5. Persist the log entry and extraction result; award XP
    facts: ExtractedFacts | None = None
    xp_result: XPResult | None = None
    async with AsyncSessionLocal() as session:
        log = Log(telegram_user_id=message.from_.id, text=message.text or "")
        session.add(log)
        await session.flush()

        try:
            habit_plans = await get_habit_plan_context(session, message.from_.id)
            facts = await extract(message.text or "", habit_plans)
            ef = ExtractedFactsModel(
                log_id=log.id,
                habits=facts.habits,
                adherence=facts.adherence.value if facts.adherence else None,
                mood=facts.mood,
                trigger=facts.trigger,
                context=facts.context,
            )
            session.add(ef)
            await session.flush()
            xp_result = await award_xp(facts, message.from_.id, session)
            await asyncio.get_running_loop().run_in_executor(
                None, store_facts, facts, message.text or "", message.from_.id
            )
        except Exception:
            logger.exception("extraction failed for log_id=%s", log.id)

        await session.commit()

    # 6. Generate the reply
    reply_text = message.text or ""
    try:
        if _is_reflection_query(message.text or ""):
            reply_text = await _answer_reflection(message.text or "", message.from_.id)
        else:
            reply_text = await run_user_message(
                telegram_user_id=message.from_.id,
                user_text=message.text or "",
                facts=facts,
            )
    except Exception:
        logger.exception("reply generation failed")

    if xp_result and xp_result.xp_gained > 0:
        reply_text += f"\n\n+{xp_result.xp_gained} XP · Level {xp_result.new_level} \U0001f5e1️"
        if xp_result.levelled_up:
            reply_text += f"\n⬆️ LEVEL UP — you are now Level {xp_result.new_level}!"

    await _send(chat_id=message.chat.id, text=reply_text)

    return {}


_REFLECTION_PATTERNS = [
    "how was my week",
    "when do i",
    "how am i doing",
    "my patterns",
    "do i usually",
    "when do i slip",
    "when do i usually",
]


def _is_reflection_query(text: str) -> bool:
    lower = text.lower()
    return any(p.lower() in lower for p in _REFLECTION_PATTERNS)


def _is_dashboard_command(text: Optional[str]) -> bool:
    if not text:
        return False
    first = text.strip().split(maxsplit=1)[0]
    command = first.split("@", maxsplit=1)[0].casefold()
    return command in {"/start", "/dashboard", "/app"}


async def _answer_reflection(query: str, telegram_user_id: int) -> str:
    history = await asyncio.get_running_loop().run_in_executor(
        None, recall_history, query, telegram_user_id
    )
    patterns = await asyncio.get_running_loop().run_in_executor(
        None, detect_patterns, telegram_user_id
    )
    if not history and not patterns:
        return "I don't have enough history yet — keep logging and I'll start surfacing patterns!"
    context = (
        f"Recent relevant history:\n{history}\n\nAll patterns:\n{patterns}"
        if patterns
        else f"Recent relevant history:\n{history}"
    )
    context = context[:3000]  # hard cap to keep prompt size bounded
    system = (
        "You are Kaizen, a personal behavior-change coach. "
        "Answer the user's reflection question using ONLY the provided history and patterns. "
        "Be specific and cite actual entries. Be concise (3-5 sentences)."
    )
    response = await complete(
        messages=[{"role": "user", "content": query}],
        system=f"{system}\n\n{context}",
        max_tokens=400,
    )
    return next(b.text for b in response.content if b.type == "text")


async def _generate_reply(
    log_text: str, facts: ExtractedFacts | None, chunks: list, history: str = ""
) -> str:
    context = "\n\n---\n\n".join(c.content for c in chunks)
    history_section = f"\n\nUser's recent history:\n{history}" if history else ""
    system = (
        "You are Kaizen, a personal behavior-change coach. "
        "Use ONLY the provided behavioral-science techniques to give a specific, actionable reply. "
        "Name the technique you are applying. Be concise (2-4 sentences). "
        "If the user's history shows a pattern relevant to this log, reference it. "
        f"Techniques available:\n\n{context}{history_section}"
    )
    response = await complete(
        messages=[{"role": "user", "content": log_text}],
        system=system,
        max_tokens=300,
    )
    return next(b.text for b in response.content if b.type == "text")
