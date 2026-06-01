# CLAUDE.md

Operating instructions for any Claude Code agent (main or sub) working in this repo.
Read this first, then read the spec for whatever milestone you are working on
(`docs/milestones/`). The product intent lives in `docs/PRODUCT.md`.

---

## Project: Kaizen

Kaizen is an **agentic behavior-change companion**. The user logs daily life in
natural language through a **Telegram bot**; the system extracts structure from
each log, remembers it across weeks, retrieves grounded behavioral-science
techniques, detects personal patterns, and **proactively decides when to
intervene**.

It is a single-user personal tool **and** a portfolio project. Code quality,
measurable results, and clean commit history matter as much as features — this
repo is meant to be read by a hiring engineer.

### Architecture (one paragraph)

Telegram → FastAPI webhook → a LangGraph agent loop. The agent calls three
tools: a structured-output extractor, a RAG retriever (embeddings + pgvector +
rerank), and a memory layer (Mem0). Everything persists in PostgreSQL with
pgvector. A scheduler wakes the agent on a cadence; the agent reasons over
recent state and decides whether a proactive nudge adds value. Langfuse traces
every model call.

---

## Tech stack

- **Language:** Python 3.12, fully type-hinted, `async` throughout.
- **Web:** FastAPI (the Telegram webhook + internal scheduler endpoint).
- **Agent:** LangGraph for the agent loop / state machine.
- **LLM:** one provider client behind `app/llm/client.py` — never call a vendor
  SDK directly anywhere else.
- **Data:** PostgreSQL + pgvector. SQLAlchemy (async) + Alembic migrations.
- **RAG:** embeddings + pgvector similarity + a reranking step.
- **Memory:** Mem0.
- **Validation:** Pydantic v2 for every structured LLM output and every API body.
- **Observability:** Langfuse.
- **Tooling:** `uv` (env + deps), `ruff` (lint + format), `pytest` (+ `pytest-asyncio`).

## Repo layout (target)

```
app/
  main.py            # FastAPI app + routes (webhook, scheduler tick, health)
  config.py          # settings from env (pydantic-settings)
  llm/client.py      # the ONLY place a vendor SDK is imported
  agent/             # LangGraph graph, nodes, tools
  extract/           # log -> typed facts (Pydantic schemas)
  rag/               # corpus loading, embeddings, retrieval, rerank
  memory/            # Mem0 integration
  db/                # SQLAlchemy models, session, migrations
  telegram/          # bot send/receive helpers
tests/               # mirrors app/, one test module per package
corpus/              # behavioral-science source chunks (markdown)
docs/                # PRODUCT.md + milestones/
.claude/agents/      # subagent definitions
```

---

## Commands

```bash
uv sync                       # install deps
cp .env.example .env          # then fill in secrets (never commit .env)
uv run alembic upgrade head   # apply migrations
uv run uvicorn app.main:app --reload   # run locally
uv run pytest                 # run tests
uv run pytest tests/extract   # run one package's tests
uv run ruff check . && uv run ruff format .   # lint + format
```

If a command above does not exist yet, you are probably in an early milestone —
create it as part of that milestone, do not invent a different toolchain.

---

## Behavioral rules (Karpathy)

Adapted from the `andrej-karpathy-skills` CLAUDE.md by Andrej Karpathy /
forrestchang, which targets the most common LLM coding failure modes. These
bias toward caution over speed; for trivial tasks, use judgment. To pull the
canonical version verbatim instead:
`curl https://raw.githubusercontent.com/forrestchang/andrej-karpathy-skills/main/CLAUDE.md`

**1. Think before coding.** State your assumptions out loud before implementing.
If the request has more than one reasonable interpretation, surface them — do
not silently pick one. If a simpler approach exists, say so. If something is
unclear, stop and ask rather than guessing.

**2. Simplicity first.** Write the minimum code that solves the stated problem.
No speculative features, no abstractions for single-use code, no configurability
nobody asked for, no error handling for impossible cases. If a senior engineer
would call it overcomplicated, simplify it.

**3. Surgical changes.** Touch only what the task requires. Do not reformat,
rename, or "improve" adjacent code. Match the existing style even if you'd do it
differently. Remove only the imports/variables your own change orphaned; flag
unrelated dead code instead of deleting it. Every changed line must trace
directly to the request.

**4. Goal-driven execution.** Turn each task into a verifiable goal with a
check, then loop until it passes. "Add validation" becomes "write tests for
invalid inputs, then make them pass." For multi-step work, state a short plan as
`step → verify` pairs before starting.

---

## Project-specific guidelines

These merge with the rules above and win on conflict.

- **One LLM gateway.** All model calls go through `app/llm/client.py`. It owns
  retries, timeouts, and Langfuse tracing. No vendor SDK import anywhere else.
- **Every structured LLM output is a Pydantic model.** No parsing free-text with
  regex. If the model returns invalid JSON, that is a validation error to handle,
  not a string to massage.
- **Secrets come from env only** (`app/config.py`). Never hardcode keys or the
  Telegram token. `.env` is gitignored; keep `.env.example` current.
- **Single-user guard.** The bot serves exactly one Telegram user ID (allowlist
  in config). Reject everything else. No auth system in v1.
- **Migrations, not manual DDL.** Schema changes go through Alembic.
- **Tests track acceptance criteria.** Each milestone's acceptance criteria
  should map to tests under `tests/`. A milestone is not done until they pass.
- **Cost discipline.** Default to the cheapest model that meets the bar; cache
  embeddings; cap proactive messages per day (see milestone 5).
- **Privacy.** Logs are personal. Do not add third-party calls beyond the LLM
  provider, embeddings, and Langfuse without flagging it first.

---

## Subagent strategy

Work is delegated to scoped subagents defined in `.claude/agents/`. Each owns a
slice of the stack and has only the tools it needs. The main session stays the
orchestrator: it reads the milestone spec, delegates implementation, and runs
the review agent before considering anything done.

| Subagent | Owns | Used for milestones |
|---|---|---|
| `backend-engineer` | FastAPI, Telegram webhook, DB models, migrations | 1, (all) |
| `rag-engineer` | corpus, embeddings, pgvector, retrieval, rerank | 3 |
| `agent-engineer` | LangGraph loop, tools, Mem0, proactive triggers | 4, 5 |
| `eval-engineer` | eval harness, LLM-as-judge, Langfuse wiring | 6 |
| `code-reviewer` | read-only review against these rules (run before "done") | all |

Delegation notes (these reflect how subagents actually work):
- A subagent starts with a **fresh context** — the only thing it receives is the
  prompt you give it. Put the milestone file path, relevant code paths, and the
  acceptance criteria directly in the delegation prompt.
- It returns **only its final result** to the main session; intermediate file
  reads stay in its own context. Good for keeping the orchestrator clean.
- Use `code-reviewer` (read-only) proactively before commits, especially on
  anything touching the webhook, secrets, or the DB.
- Create/edit subagents with `/agents` or by editing the markdown files directly;
  restart the session to pick up new agent files.

## Definition of done (every task)

1. Acceptance criteria for the milestone met and covered by tests.
2. `uv run pytest` green; `uv run ruff check .` clean.
3. `code-reviewer` ran and its findings addressed.
4. Diff is surgical — every line traces to the task.
