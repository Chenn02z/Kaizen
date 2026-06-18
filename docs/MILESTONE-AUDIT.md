# Kaizen Milestone Audit

Last reviewed: 2026-06-18

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
| `08-dashboard` | partially implemented | `docs/milestones/08-dashboard.md`, `tests/test_dashboard.py`, `tests/test_webhook.py` | Backend read model and Telegram command launch exist. Frontend completeness and Milestone 8 acceptance still need final verification. |
| `09-correction-loop` | planned | `docs/milestones/09-correction-loop.md` | Chat-based corrections and auditable evidence overrides are needed because extraction intentionally prefers precision over recall. |
| `10-lesson-grounded-reflection` | planned | `docs/milestones/10-lesson-grounded-reflection.md` | Reflection questions and proactive ticks should retrieve self-authored lesson notes when the user asks what to change or when a nudge is justified. |

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

- Milestone 8 still needs final verification against the Telegram Mini App
  acceptance criteria, especially frontend rendering and production launch
  behavior.
- Reflection questions currently use memory/history, but action-oriented
  reflection does not yet retrieve lessons from the RAG corpus.
- Proactive tick retrieval can still become too generic unless the lesson query
  is built from due habits, recent drift, triggers, and memory.

## Recommended next implementation step

Build in this order:

1. Milestone 8: Telegram-native Mini App launch, dashboard read model, and
   read-only review sections.
2. Milestone 9: correction loop, so trusted habit state can be repaired before
   it drives more nudges.
3. Milestone 10: lesson-grounded reflection and lesson-aware proactive retrieval.

That keeps the product focused on the core wedge: natural-language logs become
trusted habit state, and Kaizen applies the builder's own grounded lessons only
when they fit the user's real history.
