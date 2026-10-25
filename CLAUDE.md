# CLAUDE.md

Operating instructions for Claude Code in this repo.

- Product intent: `docs/PRODUCT.md`
- Target architecture and stack: `docs/ARCHITECTURE.md`
- Agent harness, graph and module contract: `docs/HARNESS.md`

## Project: Kaizen

Kaizen is a personal second brain in Telegram for one user. The user logs
daily life in natural language. A single orchestration agent extracts
structure, remembers across weeks, grounds advice in the builder's own lesson
notes, and decides when a reply or a proactive nudge is worth sending.

It is a single-user personal tool and a portfolio project. Code quality,
measurable results (evals), and clean commit history matter as much as features.

**Scope right now:** the `core`, `knowledge` and `habits` modules only. Do not
build or scaffold other modules.

## Architecture (Target)

Telegram → FastAPI webhook → **harness** (auth, save raw log, extraction,
context, budgets, outbox) → **orchestrator** (LangGraph loop: `prepare → agent ⇄
tools → finalize`) → module tools → Postgres/pgvector + Mem0.

- **The orchestrator decides; the harness guarantees; modules provide.**
  Judgment (what to read/write, whether to reply, what to say, when to check
  back) belongs to the agent. Security, data loss, spam limits and budgets
  belong in harness code, never in prompts.
- Modules live in `app/modules/<name>/` and own their tables (`<name>_*`),
  services, tools, extraction section, context snippet, jobs and tests.
- **Modules never import each other.** Cross-module logic lives in the orchestrator.

The repo is migrating from the old fixed graph (`app/agent/graph.py`) to this
design. Follow the migration order in `docs/HARNESS.md`. Until a piece is
moved, match the existing code where it currently lives.

## Tech Stack

- Python 3.12, fully type-hinted, async throughout.
- FastAPI (webhook + internal wake endpoint).
- LangGraph for the orchestrator loop and Postgres checkpointing. No LangChain
  chat models or `ToolNode`.
- OpenRouter as the model gateway, called only from `app/llm/client.py`.
- PostgreSQL + pgvector (Supabase), SQLAlchemy async, Alembic.
- Mem0 for long-term memory. pgvector + rerank for knowledge retrieval.
- Pydantic v2 for every structured model output, tool input and API body.
- APScheduler in-process. Jobs are saved in Postgres.
- Langfuse for tracing and eval datasets.
- Tooling: `uv`, `ruff`, `pytest`, `pytest-asyncio`.
- Dashboard: Google Sheet rewritten nightly (no frontend code).
- Hosting: Oracle Cloud VM (systemd + Caddy, `deploy/oracle/`). Local DB:
  `docker compose up -d db`.

## Commands

```bash
uv sync
cp .env.example .env
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
uv run pytest
uv run ruff check .
uv run ruff format .
```

## Repository Rules

- Keep changes surgical. Touch only what the task requires and match existing style.
- Prefer the simplest implementation that meets the acceptance criteria. No
  speculative abstractions, unused config, or scaffolding for future modules.
- All model and embedding calls go through `app/llm/client.py`. Do not import
  vendor SDKs anywhere else.
- Every structured LLM output and every tool input is a Pydantic model. Never
  parse model free text with regex.
- Hard limits (allowed user, daily proactive cap, quiet hours, step/token/time
  budgets) are enforced in harness code and covered by deterministic tests.
- Write tools record an audit row. Refusals are returned to the agent as tool
  results, not raised.
- Secrets come from env/config only. Never commit `.env`. Keep `.env.example`
  current when config changes.
- The bot serves exactly one Telegram user ID from config. Reject all others.
- Schema changes go through Alembic migrations, not manual DDL.
- Default to the cheapest model that passes evals. Cache embeddings.
- Logs are personal. Flag any new third-party call before adding it (allowed:
  OpenRouter, Langfuse, Telegram, Google Sheets, Supabase).

## Definition Of Done

1. The change is covered by tests. Agent behavior changes also get an eval case.
2. `uv run pytest` passes for the touched area, or the reason it could not be
   run is reported.
3. `uv run ruff check .` is clean for Python changes, or the reason is reported.
4. The diff is surgical and every changed line traces to the task.
