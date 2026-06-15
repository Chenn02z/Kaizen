---
name: kaizen-backend
description: "Build and edit Kaizen backend code: FastAPI, Telegram webhook, async SQLAlchemy models, Alembic migrations, config, and the single LLM gateway."
---

# Kaizen Backend

Use this skill for backend, web, database, config, Telegram, and LLM gateway
work.

## Scope

- `app/main.py`
- `app/config.py`
- `app/db/`
- `app/telegram/`
- `app/llm/client.py`
- Alembic migrations
- Backend tests under `tests/`

## Workflow

1. Read `AGENTS.md` and any relevant milestone spec under `docs/milestones/`.
2. Inspect existing routes, models, config, and tests before editing.
3. Add or update tests that express the behavior or acceptance criteria.
4. Implement narrowly using async Python and existing project patterns.
5. Run focused tests, then `uv run ruff check .` when Python files changed.

## Rules

- All model and embedding calls go through `app/llm/client.py`.
- Vendor SDK imports belong only in the LLM gateway.
- Secrets come from env/config only. Never touch or commit `.env`.
- Keep `.env.example` current when adding required settings.
- Enforce the single-user Telegram allowlist on inbound requests.
- Schema changes require Alembic migrations.
- Use Pydantic v2 for API bodies and structured LLM outputs.
