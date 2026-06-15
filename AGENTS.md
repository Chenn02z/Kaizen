# AGENTS.md

Operating instructions for Codex working in this repo. Read this first, then
read the relevant milestone spec under `docs/milestones/`. Product intent lives
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
state. A scheduler wakes the agent on a cadence; the agent reasons over recent
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
- Frontend: Telegram Mini App in `webapp/` using React, TypeScript, Vite,
  `@telegram-apps/sdk-react`, and `@telegram-apps/telegram-ui`.

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

If a command does not exist yet, the repo is probably in an early milestone.
Create the expected command as part of that milestone; do not invent a different
toolchain.

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
- Tests track milestone acceptance criteria. A milestone is not done until the
  relevant tests pass.
- Default to the cheapest model that meets the bar; cache embeddings and cap
  proactive messages per day where required.
- Logs are personal. Do not add third-party calls beyond the LLM provider,
  embeddings, and Langfuse without flagging it first.

## Codex Workflows

Repo-scoped skills live under `.agents/skills/`. Use them when the task matches
their scope:

- `$kaizen-milestone` for milestone implementation planning and verification.
- `$kaizen-backend` for FastAPI, Telegram, DB, migrations, config, and LLM
  gateway work.
- `$kaizen-rag` for corpus, embeddings, pgvector retrieval, reranking, and
  grounded replies.
- `$kaizen-agent` for LangGraph, memory, scheduler, and proactive intervention
  logic.
- `$kaizen-evals` for golden sets, judge rubrics, reports, and Langfuse
  observability.
- `$kaizen-frontend` for the Telegram Mini App and `/miniapp` serving glue.
- `$teach` for repo-grounded lessons, learning records, and interview-oriented
  explanations tied to Kaizen work.

Custom Codex subagents live under `.codex/agents/`. Use subagents only when the
user explicitly asks for parallel/delegated agent work. The reviewer agent is
read-only and suitable before considering significant work done.

## Definition Of Done

1. Acceptance criteria for the relevant milestone are met and covered by tests.
2. `uv run pytest` passes for the touched area, or the reason it could not be
   run is reported.
3. `uv run ruff check .` is clean for Python changes, or the reason it could not
   be run is reported.
4. For frontend changes, `npm run build` in `webapp/` passes, or the reason it
   could not be run is reported.
5. The diff is surgical and every changed line traces to the task.
