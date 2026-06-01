# Milestone 1 — Skeleton

**Goal:** A Telegram bot that receives your messages through a FastAPI webhook
and stores each one in PostgreSQL. Nothing intelligent yet — just the spine.

**Unlocks:** the deployable foundation everything else hangs off; resume keywords
FastAPI, webhook/event-driven architecture, PostgreSQL.

**Owner subagent:** `backend-engineer`

## Scope

In: FastAPI app, Telegram webhook endpoint, message echo, Postgres connection,
`logs` table, migrations, config from env, single-user allowlist, health check.

Out: extraction, RAG, memory, the agent, any LLM call. Do not add them here.

## Prerequisites

None. This is the entry point.

## Tasks

- [ ] `uv` project, `ruff` + `pytest` configured.
- [ ] `app/config.py` reads `TELEGRAM_TOKEN`, `ALLOWED_USER_ID`, `DATABASE_URL`
      from env; `.env.example` committed, `.env` gitignored.
- [ ] `app/db/` async SQLAlchemy engine/session + Alembic; `logs` table
      (id, telegram_user_id, text, created_at).
- [ ] `app/telegram/` send + receive helpers.
- [ ] `POST /webhook`: verify sender is the allowed user, persist the message,
      echo it back.
- [ ] `GET /health` returns 200.
- [ ] README note on registering the webhook with Telegram (ngrok for local).

## Acceptance criteria (verify each)

- Sending a Telegram message persists exactly one `logs` row → verify by query.
- The bot echoes the message back to you → verify in the chat.
- A message from any other user ID is rejected and stored nothing → test.
- `uv run pytest` green; `uv run uvicorn app.main:app` boots clean.

## Definition of done

Acceptance criteria met and tested, lint clean, `code-reviewer` run, diff
surgical.

## Resume bullet unlocked

Built a Telegram-bot interface on a FastAPI webhook with single-user
authorization and persistent logging in PostgreSQL.
