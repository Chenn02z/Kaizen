from collections.abc import Mapping
from typing import Any

import httpx

from app.config import settings


async def send_message(
    chat_id: int,
    text: str,
    reply_markup: Mapping[str, Any] | None = None,
) -> None:
    """Send a text message to a Telegram chat via the Bot API."""
    url = f"https://api.telegram.org/bot{settings.telegram_token}/sendMessage"
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = dict(reply_markup)
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
