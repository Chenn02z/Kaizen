# Kaizen Architecture

Target end state for the refresh. Agent design (graph, module contract,
guardrails) is in `docs/HARNESS.md`. The product contract is in `docs/PRODUCT.md`.

## Positioning

Kaizen is a **personal second brain** in Telegram. One central orchestration
agent is the only thing the user talks to. Each area of life it manages
(habits, knowledge, ...) is a separate **module** that plugs into the
orchestrator by providing tools, context and extraction. The orchestrator
reasons across modules. The modules never talk to each other directly.

| Module | Status | Manages |
|---|---|---|
| `core` | Always on | Conversation, messaging, scheduling, long-term memory |
| `knowledge` | Built (as RAG today) | The builder's lesson notes and techniques, grounding |
| `habits` | Built | Habit plans, evidence, streaks, corrections, check-ins |

New areas are added as new modules. The
orchestrator itself doesn't change.

## One-Line Summary

Telegram → FastAPI → **harness** (auth, persistence, extraction, limits) →
**orchestrator** (LangGraph loop over tools from all enabled modules) →
module services → Postgres/pgvector, Mem0, external APIs. Every model call goes
through one gateway (OpenRouter) and is traced in Langfuse.

## Stack

| Layer | Tool | Used for | Notes |
|---|---|---|---|
| Language | Python 3.12, async, fully typed | Everything | |
| Package / lint / test | `uv`, `ruff`, `pytest`, `pytest-asyncio` | Tooling | |
| Chat surface | Telegram Bot API (webhook) | Only UI: logs, replies, commands | Single allowed user ID from config |
| HTTP server | FastAPI + uvicorn | `/telegram/webhook`, `/internal/wake`, `/healthz` | |
| Agent runtime | **LangGraph** | Orchestrator loop (`StateGraph`), checkpointing, recursion limit, `interrupt()` | No LangChain models or `ToolNode`. Nodes call our own gateway |
| Checkpointer | `langgraph-checkpoint-postgres` | Saves conversation state per thread, resumes interrupted turns | Same Supabase DB |
| Model gateway | **OpenRouter** (OpenAI-compatible API) via `openai` SDK | Chat, tool calling, structured output | One API key, models switchable in config |
| Embeddings | OpenRouter embeddings endpoint, or OpenAI direct as fallback | Knowledge chunks, memory | Cached by content hash |
| Gateway module | `app/llm/client.py` | **The only** place that imports a vendor SDK | Retries, usage reporting, Langfuse |
| Structured output | Pydantic v2 | Tool inputs, extraction, API bodies | `model_json_schema()` → tool definitions |
| Database | PostgreSQL + pgvector on Supabase | All module tables, jobs, checkpoints | Local: `docker compose up -d db` |
| ORM / migrations | SQLAlchemy async + Alembic | All schema changes | No manual DDL. Tables prefixed per module |
| Knowledge retrieval | pgvector similarity + LLM rerank | `knowledge` module | |
| Long-term memory | Mem0 (backed by pgvector) | `core` memory tools | Shared across modules |
| Scheduling | APScheduler (in-process) + `core_scheduled_jobs` table | Daily wakeups, module jobs, agent follow-ups | Saved in Postgres so jobs survive restarts |
| Observability | Langfuse | Traces per turn, model call and tool call (tagged by module); eval datasets | |
| Evals | pytest + Langfuse datasets | Per-module and cross-module suites | |
| Dashboard | Google Sheets API | Nightly rewrite, one tab per module | No frontend code |
| Hosting | Oracle Cloud VM, systemd + Caddy | App process + TLS | See `deploy/oracle/` |

### Model Choice (via OpenRouter)

| Role | Default | Why |
|---|---|---|
| Orchestrator | Small, fast tool-calling model | Runs every turn. Upgrade if cross-module reasoning evals fail |
| Intake extraction | Same cheap model, structured output | One call per log |
| Rerank | Cheapest model that passes evals | Short prompt |
| Weekly review | Larger model (optional) | Rare, quality matters |

Models are chosen in config (`LLM_MODEL_AGENT`, `LLM_MODEL_EXTRACT`, ...).
Switching providers changes config only, not code.

**Data flow to flag:** Third-party services are limited to: OpenRouter (+ the
upstream model provider), Langfuse, Telegram, Google Sheets, Supabase.

## Components

```
                ┌──────────────┐
  Telegram ───▶ │   FastAPI    │ ◀─── APScheduler
                └──────┬───────┘      (daily wakeups, module jobs, follow-ups)
                       ▼
        ┌──────────────────────────────┐
        │           HARNESS            │  deterministic Python
        │ auth · persist raw log ·     │
        │ composed extraction ·        │
        │ context · budgets · outbox   │
        └──────────────┬───────────────┘
                       ▼
        ┌──────────────────────────────┐
        │   ORCHESTRATOR (LangGraph)   │──▶ Postgres checkpointer
        │   prepare → agent ⇄ tools    │
        │            → finalize        │
        └──────────────┬───────────────┘
                       │ tool registry (from enabled modules)
     ┌─────────────┬───┴─────────┐
     ▼             ▼             ▼
  ┌──────┐   ┌───────────┐   ┌────────┐
  │ core │   │ knowledge │   │ habits │
  └──┬───┘   └─────┬─────┘   └───┬────┘
     ▼             ▼             ▼
  Mem0, jobs,   pgvector     habits_*
  Telegram      chunks       tables

  All model calls ──▶ app/llm/client.py ──▶ OpenRouter ──▶ Langfuse
```

## Module Layout (End State)

```
app/
  main.py                FastAPI app, routes, lifespan
  config.py              pydantic-settings, incl. ENABLED_MODULES
  llm/client.py          complete(), complete_with_tools(), embed(): the only gateway
  db/                    engine, session, Base
  telegram/client.py     Bot API wrapper
  harness/
    intake.py            auth, dedupe, save raw log, composed extraction
    context.py           core context + each module's context()
    runner.py            invokes graph per trigger, enforces budgets
    outbox.py            daily cap, quiet hours, actual send
    registry.py          collects tools/extractors/jobs from enabled modules
  orchestrator/
    graph.py             prepare, agent, tools, finalize
    state.py
    prompts.py           core system prompt + module prompt fragments
  modules/
    base.py              Module contract (see HARNESS.md)
    core/                messaging, scheduling, memory tools
    knowledge/           lesson loading, embed, retrieve, rerank
    habits/              plan, cadence, evidence, state, corrections, tools
  dashboard.py           nightly Sheets rewrite, one tab per module
```

### Module Boundaries

- A module owns its **tables** (`<module>_*`), **services**, **tools**,
  **extraction schema**, **context snippet**, **scheduled jobs**, **prompt
  fragment** and **tests**. All of it lives in `app/modules/<name>/`.
- Modules may import `core`, `db`, `llm`, `shared`. **Modules never import each
  other.** Cross-module reasoning is the orchestrator's job, done by calling
  tools from both.
- A module can be turned off in config. Its tools, context and extraction
  section then disappear from the agent.
- Alembic migrations stay in one history, with one file per module change.

### Current Code → Modules

| Today | Moves to |
|---|---|
| `app/habits/*`, `app/corrections/*`, `app/checkins/*`, `app/gamification/*` | `modules/habits/` |
| `app/rag/*` | `modules/knowledge/` |
| `app/memory/*` | `modules/core/memory` |
| `app/extract/*` | Habits extraction schema + `harness/intake.py` composer |
| `app/agent/*` | `orchestrator/` + `harness/runner.py` |
| `app/telegram/intake.py` | `harness/intake.py` |

## Request Flows

### 1. User sends a message

1. Telegram POSTs to `/telegram/webhook`. FastAPI acknowledges right away and processes in the background.
2. **Intake:** auth → dedupe `update_id` → save `core_raw_logs` → one
   extraction call whose schema is composed from every enabled module's
   section (`habits`, ...) → each module saves its own section.
3. **Context:** core snapshot + each module's `context()` snippet.
4. **Orchestrator** runs with every enabled module's tools and replies or stays silent.
5. **Outbox** sends. The checkpoint is saved. The trace is closed.

Example: "skipped gym again, too tired". Extraction fills `habits` (gym:
missed). The agent can call `habits.get_state`, `core.recall_memory` and
`knowledge.search` to spot the pattern and suggest a grounded technique.

### 2. Scheduled wakeup

- **Core daily wakeup:** the orchestrator sees all module contexts and decides
  whether anything is worth saying.
- **Module jobs** (e.g. re-embedding new lesson notes) are deterministic and
  run without the agent.
- **Agent follow-ups** (`core.schedule_followup`) start the orchestrator with
  the agent's own earlier reason.

### 3. Nightly / weekly

- Dashboard rewrite (one tab per module).
- Weekly review: orchestrator run with trigger `weekly_review` across all modules.

## Data Model

| Table | Module | Purpose |
|---|---|---|
| `core_raw_logs` | core | Every inbound message, saved before any model call |
| `core_messages_out` | core | Every bot message, trigger, reason, module (daily cap) |
| `core_scheduled_jobs` | core | Agent follow-ups + module jobs |
| `core_actions` | core | Audit row for every write tool call |
| `checkpoint_*` | core | LangGraph checkpointer |
| Mem0 tables | core | Long-term memory |
| `knowledge_chunks`, `knowledge_embedding_cache` | knowledge | Lesson corpus + vectors |
| `habits_plans`, `habits_facts`, `habits_corrections` | habits | Habit domain |

Renaming the existing tables to the prefixed names is one Alembic migration.

## Cross-Cutting Rules

- All model and embedding calls go through `app/llm/client.py`.
- Every structured model output and every tool input is a Pydantic model.
- Modules never import each other. Cross-module logic lives in the orchestrator.
- Secrets come from env only. `.env.example` stays current.
- Exactly one Telegram user ID is served. Everyone else is rejected in the harness.
- Schema changes go through Alembic. Tables are prefixed with their module name.
- Proactive messages are capped per day in the outbox, across all modules.
- Cheapest model that passes evals. Embeddings are cached.
