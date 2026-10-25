# CLAUDE.md

Operating instructions for Claude Code working in this repo. Product intent lives
in `docs/PRODUCT.md`.

## Project: Kaizen

Kaizen is an agentic behavior-change companion. The user logs daily life in
natural language through a Telegram bot; the system extracts structure from each
log, remembers it across weeks, retrieves grounded behavioral-science
techniques, detects personal patterns, and proactively decides when to
intervene.

It is a single-user personal tool and a portfolio project. Code quality,
measurable results, and clean commit history matter as much as features.

## Architecture

Telegram -> FastAPI webhook -> LangGraph agent loop. The agent calls structured
extraction, RAG retrieval, and memory tools. PostgreSQL with pgvector persists
state. An in-process APScheduler wakes the agent on a cadence; the agent reasons over recent
state and decides whether a proactive nudge adds value. Langfuse traces model
calls.

## Tech Stack

- Python 3.12, fully type-hinted, async throughout.
- FastAPI for the Telegram webhook and internal scheduler endpoint.
- LangGraph for the agent loop and state machine.
- One LLM provider gateway behind `app/llm/client.py`; do not import vendor SDKs
  anywhere else.
- PostgreSQL + pgvector, SQLAlchemy async, and Alembic migrations.
- RAG uses embeddings, pgvector similarity, and reranking.
- Memory uses Mem0.
- Pydantic v2 validates structured LLM output and API bodies.
- Langfuse provides observability.
- Tooling: `uv`, `ruff`, `pytest`, and `pytest-asyncio`.
- Dashboard: a Google Sheet rewritten nightly by the backend (no frontend code).
- Hosting: the app runs on an Oracle Cloud VM (systemd + Caddy, see `deploy/oracle/`);
  PostgreSQL + pgvector is hosted on Supabase. Local dev uses `docker compose up -d db`.

## Commands

```bash
uv sync
cp .env.example .env
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
uv run pytest
uv run pytest tests/extract
uv run ruff check .
uv run ruff format .
```

## Repository Rules

- Keep changes surgical. Touch only what the task requires and match existing
  style.
- Prefer the simplest implementation that satisfies the stated acceptance
  criteria. Do not add speculative abstractions or unused configuration.
- All model and embedding calls go through `app/llm/client.py`.
- Every structured LLM output is a Pydantic model. Do not parse model free text
  with regex.
- Secrets come from environment/config only. Never hardcode keys or tokens.
  Never commit `.env`; keep `.env.example` current when config changes.
- The bot serves exactly one Telegram user ID from config. Reject other users.
- Schema changes go through Alembic migrations, not manual DDL.
- Changes are not done until the relevant tests pass.
- Default to the cheapest model that meets the bar; cache embeddings and cap
  proactive messages per day where required.
- Logs are personal. Do not add third-party calls beyond the LLM provider,
  embeddings, and Langfuse without flagging it first.

## Definition Of Done

1. The change is covered by tests.
2. `uv run pytest` passes for the touched area, or the reason it could not be
   run is reported.
3. `uv run ruff check .` is clean for Python changes, or the reason it could not
   be run is reported.
4. The diff is surgical and every changed line traces to the task.
