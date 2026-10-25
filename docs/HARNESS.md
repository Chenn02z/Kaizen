# Kaizen Agent Harness & Framework

End-state design for the second-brain orchestrator. Stack and infrastructure
are in `docs/ARCHITECTURE.md`.

## Principle

**The orchestrator decides; the harness guarantees; modules provide.**

- The **orchestrator** (one model in a LangGraph loop) is the single agent. It
  decides what to read, what to write, whether to reply, what to say, and when
  to check back, across every area of life.
- The **harness** (plain Python) guarantees whatever must never depend on model
  behavior: who is allowed in, that no data is lost, budgets, caps, audit.
- **Modules** (core, knowledge, habits) provide domain capability as
  tools, context and extraction. They hold no agent logic of their own.

Rule of thumb: security hole, data loss or spam → harness. Judgment call →
orchestrator. Domain logic or data → module.

One agent, not one agent per module. Sub-agents would add a routing layer, more
cost, and make cross-module reasoning harder. Revisit only if the tool count
outgrows one model's context (see *Scaling*).

## Module Contract

Every module implements one small contract in `app/modules/base.py`:

```python
class Module(Protocol):
    name: str                                   # "core", "knowledge", "habits"
    prompt: str                                 # short paragraph: what this module is for
    tools: list[Tool]                           # registered as "<name>.<tool>"
    extraction: type[BaseModel] | None          # section of the intake schema

    async def context(self, ctx: TurnContext) -> str: ...
    async def save_extraction(self, log_id: int, data: BaseModel) -> None: ...
    jobs: list[Job]                             # deterministic cron jobs (optional)
```

`Tool` = name + Pydantic input model + async fn + `kind: read | write | action`.

`harness/registry.py` reads `ENABLED_MODULES` from config, imports each
module's `MODULE` object, and builds:
- the tool list for the orchestrator,
- the composed extraction schema,
- the list of context providers,
- the APScheduler jobs.

That's the whole plugin system: a list in config and one object per module. No
dynamic discovery.

### Adding a Module

1. Create `app/modules/<name>/` with models, an Alembic migration and services.
2. Define tools, an extraction section, `context()`, a prompt paragraph, and jobs.
3. Export `MODULE`, add `<name>` to `ENABLED_MODULES`.
4. Add module evals plus at least one cross-module eval.

The orchestrator, harness and other modules don't change.

## Responsibility Split

| Concern | Owner | Mechanism |
|---|---|---|
| Reject other Telegram users | Harness | `intake.py`, before anything else |
| Duplicate webhook deliveries | Harness | Unique `update_id` |
| Save raw log | Harness | Written before any model call |
| Extraction | Harness + modules | One composed call. Each module saves its section |
| Starting context | Harness + modules | Core snapshot + each `module.context()` |
| What to look up / change | Orchestrator | Module tools |
| Whether to reply / nudge, what to say | Orchestrator | `core.send_message` or nothing |
| When to check back | Orchestrator | `core.schedule_followup` |
| Domain rules (cadence, streaks, retrieval) | Module | Services behind tools |
| Background upkeep (e.g. re-embedding notes) | Module | Deterministic `jobs` |
| Daily cap, quiet hours | Harness | Outbox refuses and returns the reason as a tool result |
| Step / token / time budget | Harness | `recursion_limit`, token counter, timeout |
| Failure fallback | Harness | Fixed reply or silence, logged |
| Audit + tracing | Harness | `core_actions`, Langfuse spans tagged by module |

## Triggers

| Trigger | Source | Orchestrator should... |
|---|---|---|
| `user_message` | Telegram webhook | Normally reply (silence allowed) |
| `scheduled` | Core daily wakeup | Scan all modules, nudge or stay silent |
| `followup` | Its own earlier `schedule_followup` | Act on the stored reason |
| `weekly_review` | Weekly cron | Summarize the week, propose plan changes |

Module jobs are not triggers. They run without the agent.

## Graph

```
            ┌──────────────┐
  START ──▶ │   prepare    │   harness: core + module context, budget
            └──────┬───────┘
                   ▼
            ┌──────────────┐   tool calls   ┌──────────────┐
       ┌──▶ │    agent     │ ─────────────▶ │    tools     │
       │    └──────┬───────┘                └──────┬───────┘
       │           │ no tool calls                 │
       │           ▼                               │
       │    ┌──────────────┐                       │
       │    │   finalize   │ ──▶ END               │
       │    └──────────────┘                       │
       └───────────────────────────────────────────┘
                  (loop until done or budget hit)
```

Intake (auth, dedupe, persist, composed extraction) runs **before** the graph
in `harness/intake.py`. It's deterministic and doesn't need graph nodes.

### Nodes

**`prepare`** (deterministic)
- Input: trigger, `telegram_user_id`, optional `log_id` / follow-up reason.
- Core context: local time + timezone, last N turns, proactive count /
  remaining cap, pending follow-ups, this log's extracted sections.
- Module context: runs every enabled `module.context()` concurrently, each
  returning a few lines (e.g. habits: due today, streaks).
- Builds a system prompt from the core prompt + each module's `prompt` + the
  trigger instruction. Sets the budget.

**`agent`** (model)
- `client.complete_with_tools(system, messages, tools)` with tools from all
  enabled modules, named `<module>.<tool>`.
- Routing: tool calls → `tools`, none → `finalize`, budget used up → `finalize`.

**`tools`** (deterministic executor)
- Look up in the registry → validate against the Pydantic model → run → append
  the result.
- Validation errors and refusals come back as tool results. Exceptions are
  caught and returned as `{"error": ...}`.
- `write`/`action` tools write a `core_actions` row (module, tool, args,
  trigger, trace ID).
- Independent `read` calls run concurrently.

**`finalize`** (deterministic)
- No `send_message` means silence. Record it with the agent's last text as the reason.
- On a `user_message` trigger, if there was an error or the budget ran out with
  no reply: send the fallback ("Logged ✓").
- Flush Langfuse metadata (trigger, steps, modules touched, decision).

### State

```python
class AgentState(TypedDict):
    trigger: Literal["user_message", "scheduled", "followup", "weekly_review"]
    telegram_user_id: int
    log_id: int | None
    event: dict | None               # followup reason
    system: str                      # built by prepare
    messages: Annotated[list[dict], add_messages_like]
    steps: int
    budget_exhausted: bool
    sent_message_ids: list[int]
    error: str | None
```

Thread = `user:{telegram_user_id}`. One conversation across all modules.

## Tools by Module

### `core` (always on)

| Tool | Kind | Purpose | Guard |
|---|---|---|---|
| `core.send_message` | action | Reply / nudge / check-in (`kind`, `module?`, `text`) | Cap + quiet hours for proactive; 1 per turn |
| `core.schedule_followup` | action | Wake me at `run_at` because `reason` | ≤ 7 days, ≤ 3 pending |
| `core.cancel_followup` | action | Cancel a pending follow-up | |
| `core.recall_memory` | read | Mem0 search across all life areas | |
| `core.remember` | write | Save a long-term memory | Audited |
| `core.get_recent_logs` | read | Raw logs by date range | |

### `knowledge`

| Tool | Kind | Purpose |
|---|---|---|
| `knowledge.search` | read | Reranked lesson/technique chunks with source. Any module's advice is grounded here |

### `habits`

| Tool | Kind | Purpose | Guard |
|---|---|---|---|
| `habits.get_state` | read | Streaks, last evidence, due status | |
| `habits.get_plan` | read | Habits, cadence, targets | |
| `habits.log_evidence` | write | Manual evidence when extraction missed it | No future dates |
| `habits.record_correction` | write | Override evidence | Audited |
| `habits.update_plan` | write | Add / pause / change cadence | Explicit user intent; `interrupt()` confirm |

Extraction section: `HabitEvidence[]` (habit, date, status, note).
Context: habits due today without evidence, current streaks.

## Guardrails (Hard, in Code)

| Guard | Value (config) | Where |
|---|---|---|
| Allowed user | `TELEGRAM_ALLOWED_USER_ID` | `harness/intake.py` |
| Max loop steps | 8 | `recursion_limit` |
| Max tokens per turn | ~20k | `runner.py` |
| Turn timeout | 60s | `runner.py` |
| Proactive messages / day | 2 (across all modules) | `outbox.py` |
| Quiet hours | 00:00–07:00 local | `outbox.py` |
| Sends per turn | 1 | `core.send_message` |
| Pending follow-ups | 3 | `core.schedule_followup` |
## Prompting

- **Core system prompt:** second-brain role, brief tone, silence is valid,
  never invent data, advice must be grounded via `knowledge.search` and cite
  the source, connect across life areas when the data supports it.
- **Module fragments:** each enabled module adds one short paragraph (what it
  manages, when to use its tools).
- **Trigger instruction** + **context block** (compact text from `prepare`).

## Evals

pytest against recorded fixtures. Results go to Langfuse datasets.

| Suite | Scope | Checks |
|---|---|---|
| Extraction | per module | Precision/recall of each module's section |
| Tool choice | per module | Message → expected write tool |
| Silence | orchestrator | Scheduled / follow-up scenarios: silence vs. nudge |
| Cross-module | orchestrator | Insight uses data from ≥ 2 modules correctly, no invention |
| Grounding | orchestrator | Techniques trace back to `knowledge.search` |
| Guardrails | harness | Cap, quiet hours, budget, auth, module disabled → tools absent (no model) |

## Scaling

The single orchestrator stays until the tool list hurts accuracy or cost
(roughly 30+ tools). Next step, in order:
1. Load only the tools of modules relevant to this turn (a cheap
   classification in `prepare`, or the agent calling a `core.open_module` tool first).
2. Only then: a module becomes a sub-graph the orchestrator calls as one tool.

## Migration

| Current (`app/agent/graph.py`) | End state |
|---|---|
| `classify` | Removed. Trigger + agent judgment |
| `extract_facts` | `harness/intake.py` composed extraction (habits section) |
| `retrieve_techniques`, `retrieve_proactive_lessons` | `knowledge.search` |
| `recall` | `core.recall_memory` |
| `decide` + `intervention_policy.py` | Orchestrator judgment + outbox cap/quiet hours |
| `respond` | `core.send_message` |

Order:
1. `complete_with_tools` in `client.py` (OpenRouter).
2. `modules/base.py` + `harness/registry.py`. Move code into `core`, `knowledge`, `habits`.
3. New graph + harness behind a flag, with guardrail tests.
4. Silence / tool-choice evals on both graphs. Switch over, then delete the old graph.
5. Prefix table names (one migration).