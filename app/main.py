import logging
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.db.models import ExtractedFacts as ExtractedFactsModel
from app.db.models import Log
from app.db.session import AsyncSessionLocal
from app.extract.extractor import extract
from app.extract.schema import ExtractedFacts
from app.gamification.stats import UserStats, get_user_stats
from app.gamification.xp import XPResult, award_xp
from app.llm.client import complete
from app.rag.retrieve import retrieve
from app.telegram.client import send_message

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mini App HTML
# ---------------------------------------------------------------------------

_MINIAPP_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Kaizen</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <style>
    body { margin: 0; padding: 16px; background: #1a1a2e; color: #e0e0e0; font-family: sans-serif; }
    h1 { color: #ffd700; font-size: 1.4em; margin: 0 0 4px; }
    .subtitle { color: #888; font-size: 0.85em; margin-bottom: 20px; }
    .level-badge { font-size: 3em; font-weight: bold; color: #ffd700; text-align: center; margin: 12px 0; }
    .xp-label { font-size: 0.8em; color: #aaa; margin-bottom: 4px; }
    .bar-bg { background: #333; border-radius: 6px; height: 10px; margin-bottom: 20px; }
    .bar-fill { background: #ffd700; border-radius: 6px; height: 10px; transition: width 0.5s; }
    .habit { margin-bottom: 14px; }
    .habit-name { font-size: 0.9em; text-transform: capitalize; margin-bottom: 3px; }
    .habit-level { font-size: 0.75em; color: #ffd700; }
    .habit-bar-fill { background: #4a90d9; border-radius: 6px; height: 6px; }
    #loading { text-align: center; color: #888; margin-top: 40px; }
  </style>
</head>
<body>
  <div id="loading">Loading...</div>
  <div id="app" style="display:none">
    <h1>⚔️ Kaizen Warrior</h1>
    <div class="subtitle">Your habit RPG</div>
    <div class="level-badge" id="level">1</div>
    <div class="xp-label" id="xp-label">0 XP · 100 to next level</div>
    <div class="bar-bg"><div class="bar-fill" id="xp-bar" style="width:0%"></div></div>
    <div id="habits"></div>
  </div>
  <script>
    Telegram.WebApp.expand();
    fetch('/me?secret=__MINIAPP_SECRET__').then(r => r.json()).then(d => {
      document.getElementById('loading').style.display = 'none';
      document.getElementById('app').style.display = 'block';
      document.getElementById('level').textContent = 'Level ' + d.level;
      const nextLevelXp = 100 * d.level * d.level;
      const prevLevelXp = 100 * (d.level - 1) * (d.level - 1);
      const pct = nextLevelXp > prevLevelXp ? Math.round((d.xp - prevLevelXp) / (nextLevelXp - prevLevelXp) * 100) : 100;
      document.getElementById('xp-label').textContent = d.xp + ' XP · ' + d.xp_to_next_level + ' to next level';
      document.getElementById('xp-bar').style.width = pct + '%';
      const habitsEl = document.getElementById('habits');
      if (d.habits.length === 0) {
        const p = document.createElement('p');
        p.style.cssText = 'color:#888;font-size:0.85em';
        p.textContent = 'Log your first habit to unlock skills!';
        habitsEl.appendChild(p);
      } else {
        d.habits.forEach(h => {
          const nextHxp = 100 * h.level * h.level;
          const prevHxp = 100 * (h.level - 1) * (h.level - 1);
          const hpct = nextHxp > prevHxp ? Math.round((h.xp - prevHxp) / (nextHxp - prevHxp) * 100) : 100;
          const div = document.createElement('div');
          div.className = 'habit';
          const nameDiv = document.createElement('div');
          nameDiv.className = 'habit-name';
          nameDiv.textContent = h.name;
          const lvl = document.createElement('span');
          lvl.className = 'habit-level';
          lvl.textContent = ' Lv ' + h.level;
          nameDiv.appendChild(lvl);
          const barBg = document.createElement('div');
          barBg.className = 'bar-bg';
          const barFill = document.createElement('div');
          barFill.className = 'habit-bar-fill';
          barFill.style.width = hpct + '%';
          barBg.appendChild(barFill);
          div.appendChild(nameDiv);
          div.appendChild(barBg);
          habitsEl.appendChild(div);
        });
      }
    });
  </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Startup: register Telegram menu button
# ---------------------------------------------------------------------------


async def _register_menu_button() -> None:
    """Register the Mini App menu button with Telegram on startup."""
    if not settings.public_url:
        return
    url = f"https://api.telegram.org/bot{settings.telegram_token}/setChatMenuButton"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json={
                "menu_button": {
                    "type": "web_app",
                    "text": "My Stats",
                    "web_app": {"url": f"{settings.public_url}/miniapp"},
                }
            },
        )
        if not resp.is_success:
            logger.warning("setChatMenuButton failed: %s %s", resp.status_code, resp.text)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    await _register_menu_button()
    yield


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


@app.get("/me")
async def me(request: Request) -> UserStats:
    if settings.miniapp_secret and request.query_params.get("secret") != settings.miniapp_secret:
        raise HTTPException(status_code=403, detail="Forbidden")
    async with AsyncSessionLocal() as session:
        return await get_user_stats(settings.allowed_user_id, session)


@app.get("/miniapp", response_class=HTMLResponse)
async def miniapp() -> str:
    return _MINIAPP_HTML.replace("__MINIAPP_SECRET__", settings.miniapp_secret)


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

    # 5. Persist the log entry and extraction result; award XP
    facts: ExtractedFacts | None = None
    xp_result: XPResult | None = None
    async with AsyncSessionLocal() as session:
        log = Log(telegram_user_id=message.from_.id, text=message.text or "")
        session.add(log)
        await session.flush()

        try:
            facts = await extract(message.text or "")
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
        except Exception:
            logger.exception("extraction failed for log_id=%s", log.id)

        await session.commit()

    # 6. Generate a grounded coaching reply
    reply_text = message.text or ""
    try:
        habit_str = " ".join(facts.habits) if facts else ""
        query = f"{message.text or ''} {habit_str}".strip()
        chunks = await retrieve(query)
        if chunks:
            reply_text = await _generate_reply(message.text or "", facts, chunks)
    except Exception:
        logger.exception("reply generation failed")

    if xp_result and xp_result.xp_gained > 0:
        reply_text += f"\n\n+{xp_result.xp_gained} XP · Level {xp_result.new_level} \U0001f5e1️"
        if xp_result.levelled_up:
            reply_text += f"\n⬆️ LEVEL UP — you are now Level {xp_result.new_level}!"

    await _send(chat_id=message.chat.id, text=reply_text)

    return {}


async def _generate_reply(log_text: str, facts: ExtractedFacts | None, chunks: list) -> str:
    context = "\n\n---\n\n".join(c.content for c in chunks)
    system = (
        "You are Kaizen, a personal behavior-change coach. "
        "Use ONLY the provided behavioral-science techniques to give a specific, actionable reply. "
        "Name the technique you are applying. Be concise (2-4 sentences). "
        f"Techniques available:\n\n{context}"
    )
    response = await complete(
        messages=[{"role": "user", "content": log_text}],
        system=system,
        max_tokens=300,
    )
    return next(b.text for b in response.content if b.type == "text")
