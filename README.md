# Kaizen

Agentic behavior-change companion — Telegram bot backed by FastAPI and PostgreSQL.

## Quick start

```bash
cp .env.example .env          # fill in TELEGRAM_TOKEN, ALLOWED_USER_ID, TELEGRAM_WEBHOOK_SECRET, LLM_API_KEY, EMBED_API_KEY
docker compose up -d db       # start Postgres (pgvector/pg16) on localhost:5432
uv sync                       # install deps
uv run alembic upgrade head   # create all tables (logs, extracted_facts, corpus_chunks, gamification, interventions)
uv run python -m app.rag.load # embed the behavioral-science corpus into pgvector (see below)
uv run uvicorn app.main:app --reload
```

## Load the corpus (RAG)

The grounded-coaching corpus lives in `corpus/*.md`. After migrations, embed it
into the `corpus_chunks` (pgvector) table:

```bash
uv run python -m app.rag.load
```

This requires `EMBED_API_KEY` (and `EMBED_MODEL`) in your `.env`. It is
idempotent — each chunk is content-hashed, so re-running only re-embeds files
that changed. Run it after editing any corpus file. Retrieval (`app/rag/`)
returns empty until this has been run at least once.

## Mini App (Telegram dashboard)

The stats dashboard is a React + Vite app in `webapp/`, served by FastAPI at
`/miniapp`. Build it once before starting the API:

```bash
cd webapp && npm install && npm run build   # outputs webapp/dist/, served at /miniapp
```

For live frontend dev with hot reload, run `npm run dev` in `webapp/` (it proxies
`/me` to the API on `localhost:8000`). The API serves `/miniapp` only when a
build exists; without one it returns HTTP 503.

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
