# Kaizen

Kaizen is a personal habit-change companion built as a Telegram bot.

Existing habit apps helped me track intentions, but they still relied on me to
open the app, interpret my own patterns, and recover after I drifted. That did
not change my behavior. I built Kaizen to live in Telegram, where logging is
low-friction and accountability can reach me in the flow of daily life.

The product goal is not generic AI coaching. Kaizen should take natural-language
logs, turn them into structured behavioral history, surface a read-only Google
Sheets dashboard, remember personal patterns, and send a context-aware `nudge` when I
am starting to slip.

Tech stack: FastAPI, LangGraph, PostgreSQL + pgvector (Supabase), Mem0, and
Langfuse, hosted on an Oracle Cloud VM.

## What Kaizen is for

- Log the day in natural language through Telegram.
- Build a persistent history of habits, adherence, mood, triggers, and context.
- Answer reflection questions like "how did this week go?" using real history.
- Deliver grounded, timely accountability instead of motivational filler.

## Quick start

```bash
cp .env.example .env          # fill in TELEGRAM_TOKEN, ALLOWED_USER_ID, TELEGRAM_WEBHOOK_SECRET, LLM_API_KEY, EMBED_API_KEY
docker compose up -d db       # local Postgres (pgvector/pg16) on localhost:5432
uv sync                       # install deps
uv run alembic upgrade head   # create all tables (logs, extracted_facts, corpus_chunks, gamification, interventions)
uv run python -m app.rag.load # embed the behavioral-science corpus into pgvector (see below)
uv run uvicorn app.main:app --reload
```

## Deployment

Production runs the app on an Oracle Cloud VM (systemd + Caddy for HTTPS) and
the database on Supabase. See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Correction loop

If Kaizen misreads a `log`, correct it directly in Telegram instead of waiting
for the next day. V1 supports explicit chat corrections such as:

- `count that as gym`
- `count my last log as partial for gym`
- `undo gym credit for today`
- `mark sleep as missed`
- `that was not a workout`

Corrections are append-only audit records. Kaizen keeps the original `log` and
original extracted facts, applies the newest correction to habit-state
computation, updates XP/progress from the corrected state, and marks corrected
evidence in the dashboard.

## Check-in replies

When Kaizen sends a fallback check-in like `did you complete read today?`, reply
in Telegram with:

- `yes`
- `partial`
- `no`

For a multi-habit check-in, include each habit name with its status, for example:

- `gym yes, read no`
- `leetcode partial, read yes`

Check-in replies are only applied when there is a same-day fallback check-in.
They are stored as append-only evidence, update XP/progress from effective habit
state, and keep the original check-in intervention visible in the dashboard.

## Habit-plan commands

Review and update tracked habits directly in Telegram:

- `/habits` shows the current plan grouped by category.
- `/habit_add` starts a structured flow for one new habit: name, category,
  cadence, success condition, aliases, and final confirmation.
- `/habit_edit <habit>` edits one existing habit. Send one field at a time, for
  example `aliases: gym, lifted` or `cadence: 3x/week`, then send `yes` to save.

Supported cadence inputs are `daily`, `weekdays`, specific weekdays such as
`mon/wed/fri`, and weekly targets such as `3x/week`. Send `cancel` during an
add or edit flow to discard the pending change. Commands are handled before
ordinary log persistence, so they do not create `logs` rows.

V1 habit renames update the current plan, habit progress, and evidence override
references, but old `logs` and `extracted_facts` rows remain append-only
historical records.

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

## Register the Telegram webhook (local dev)

```bash
ngrok http 8000
# set PUBLIC_URL=https://<ngrok-host> in .env, then start the app
```

On startup the app calls `setWebhook` with `PUBLIC_URL/webhook` and
`TELEGRAM_WEBHOOK_SECRET`. Telegram sends that secret in the
`X-Telegram-Bot-Api-Secret-Token` header on every update; the server rejects
requests that omit or mismatch it with HTTP 403.

## Run tests

```bash
uv run pytest
```

Tests require the Docker Postgres to be running (`docker compose up -d db`).
