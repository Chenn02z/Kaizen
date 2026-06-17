# Kaizen Milestone Audit

Last reviewed: 2026-06-17

This audit compares the milestone specs in `docs/milestones/` against the
current implementation and tests in the repo.

## Status summary

| Milestone | Status | Evidence | Main gaps or notes |
|---|---|---|---|
| `01-skeleton` | implemented | `tests/test_health.py`, `tests/test_webhook.py` | Webhook + single-user guard + DB persistence are in place. |
| `02-extraction` | implemented and habit-plan-aware | `tests/extract/test_extractor.py`, `tests/habits/test_habit_plan.py` | Extraction filters to known habits from the habit plan and preserves precision bias. |
| `03-rag` | implemented | `tests/rag/test_rag.py`, `tests/evals/test_golden_and_rerank.py`, `evals/RESULTS.md` | Grounded retrieval, reranking, and reply generation exist. Corpus size is smaller than the original 100–200 chunk ambition. |
| `04-gamification` | implemented | `tests/gamification/test_xp.py`, `/me`, `/miniapp` routes | Works as an XP/progress layer. The Mini App now needs Milestone 8 to become the main read-only review surface. |
| `05-memory` | partially implemented | `tests/memory/test_memory.py` | Memory recall and bounded reflection context exist. Pattern detection is still shallow and not yet expressed against a first-class habit plan. |
| `06-proactive-agent` | partially implemented | `tests/agent/test_proactive.py`, `tests/habits/test_habit_plan.py` | Proactive nudges, silence decisions, scheduler, daily cap, due-habit evaluation, and same-day fallback `check-in`s exist. Quiet-hours configuration and richer engagement tracking remain shallow. |
| `07-evals-observability` | partially implemented | `tests/evals/*`, `evals/RESULTS.md`, `app/llm/client.py` | Retrieval and judge harness exist, and Langfuse wiring exists. A real intervention/adherence correlation report is still missing. |
| `08-dashboard` | planned | `docs/milestones/08-dashboard.md` | Read-only Telegram Mini App dashboard for habit state, recent logs, progress, and interventions. |

## Key findings

### What is genuinely implemented

- The Telegram webhook, DB persistence, habit-plan-aware extraction flow, RAG
  retrieval, gamification, memory recall, proactive agent loop, fallback
  `check-in`s, and eval harness all exist in working form.
- The current focused test slices pass when the local Postgres dependency is
  running.

### What was stale or misleading

- Memory tests had drifted from the current `mem_search` / `mem_get_all`
  implementation and were updated.
- The `/me` test had drifted from the current secret-protected route contract
  and was updated.
- Reflection-query handling existed as helper code but was not wired into the
  webhook path; this is now fixed.

### What still does not match the tightened product direction

- The Mini App is still a stats sheet rather than the main `dashboard`.
- There is no read model for today's habit state, recent `log`s, or recorded
  `intervention`s.
- Telegram launch still needs a first-class `web_app` command path, not just a
  startup menu-button registration.

## Recommended next implementation step

Build Milestone 8 first:

1. Telegram-native Mini App launch from `/start` and `/dashboard`
2. dashboard read model over habits, logs, progress, and interventions
3. read-only Mini App sections for today, habits, recent logs, and interventions
4. docs for BotFather/public URL setup

That is the shortest path from the current implementation to the product
behavior defined in `docs/PRODUCT.md`, `docs/CONTEXT.md`, and
`docs/milestones/08-dashboard.md`.
