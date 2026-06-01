# Kaizen

Agentic behavior-change companion — Telegram bot backed by FastAPI and PostgreSQL.

## Quick start

```bash
cp .env.example .env          # fill in TELEGRAM_TOKEN, ALLOWED_USER_ID, TELEGRAM_WEBHOOK_SECRET
docker compose up -d db       # start Postgres (pgvector/pg16) on localhost:5432
uv sync                       # install deps
uv run alembic upgrade head   # create the logs table
uv run uvicorn app.main:app --reload
```

## Register the Telegram webhook (local dev)

```bash
# Expose local port via ngrok
ngrok http 8000

# Register with Telegram — replace <TOKEN>, <NGROK_URL>, and <SECRET>
curl "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://<NGROK_URL>/webhook" \
  -d "secret_token=<TELEGRAM_WEBHOOK_SECRET>"
```

The `secret_token` value must match `TELEGRAM_WEBHOOK_SECRET` in your `.env`.
Telegram sends it in the `X-Telegram-Bot-Api-Secret-Token` header on every
update; the server rejects requests that omit or mismatch it with HTTP 403.

## Run tests

```bash
uv run pytest
```

Tests require the Docker Postgres to be running (`docker compose up -d db`).
