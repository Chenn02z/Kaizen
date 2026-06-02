import logging
from collections.abc import Awaitable, Callable
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import settings
from app.db.models import ExtractedFacts as ExtractedFactsModel
from app.db.models import Log
from app.db.session import AsyncSessionLocal
from app.extract.extractor import extract
from app.extract.schema import ExtractedFacts
from app.llm.client import complete
from app.rag.retrieve import retrieve
from app.telegram.client import send_message

app = FastAPI(title="Kaizen")
logger = logging.getLogger(__name__)


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

    # 5. Persist the log entry and extraction result
    facts: ExtractedFacts | None = None
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
