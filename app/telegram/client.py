import httpx

from app.config import settings

_API = f"https://api.telegram.org/bot{settings.telegram_token}"


async def send_message(chat_id: int, text: str) -> None:
    """Send a text message to a Telegram chat via the Bot API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{_API}/sendMessage", json={"chat_id": chat_id, "text": text})
        response.raise_for_status()


async def set_webhook(url: str, secret: str) -> None:
    """Point Telegram at our webhook; idempotent, so safe to call on every startup."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{_API}/setWebhook",
            json={"url": url, "secret_token": secret, "allowed_updates": ["message"]},
        )
        response.raise_for_status()
