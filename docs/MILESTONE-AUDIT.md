# Kaizen Milestone Audit

Last reviewed: 2026-06-15

This audit compares the milestone specs in `docs/milestones/` against the
current implementation and tests in the repo.

## Status summary

| Milestone | Status | Evidence | Main gaps or notes |
|---|---|---|---|
| `01-skeleton` | implemented | `tests/test_health.py`, `tests/test_webhook.py` | Webhook + single-user guard + DB persistence are in place. |
| `02-extraction` | implemented on the current code path, but not yet aligned with the new habit-plan direction | `tests/extract/test_extractor.py` | Extraction still emits generic habit strings. It is not yet grounded against a first-class habit plan. |
| `03-rag` | implemented | `tests/rag/test_rag.py`, `tests/evals/test_golden_and_rerank.py`, `evals/RESULTS.md` | Grounded retrieval, reranking, and reply generation exist. Corpus size is smaller than the original 100–200 chunk ambition. |
| `04-gamification` | implemented | `tests/gamification/test_xp.py`, `/me`, `/miniapp` routes | Works, but it is a retention layer rather than part of the core accountability loop. |
| `05-memory` | partially implemented | `tests/memory/test_memory.py` | Memory recall and bounded reflection context exist. Pattern detection is still shallow and not yet expressed against a first-class habit plan. |
| `06-proactive-agent` | partially implemented | `tests/agent/test_proactive.py` | Current proactive nudges, silence decisions, scheduler, and daily cap work. Due-habit evaluation and same-day fallback `check-in` behavior are not implemented yet. |
| `07-evals-observability` | partially implemented | `tests/evals/*`, `evals/RESULTS.md`, `app/llm/client.py` | Retrieval and judge harness exist, and Langfuse wiring exists. A real intervention/adherence correlation report is still missing. |

## Key findings

### What is genuinely implemented

- The Telegram webhook, DB persistence, extraction flow, RAG retrieval,
  gamification, memory recall, proactive agent loop, and eval harness all exist
  in working form.
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

- There is still no first-class habit-plan source of truth in the code.
- Extraction is not yet habit-plan-aware.
- Proactive behavior does not yet reason over due habits or send fallback
  `check-in`s before escalating to a grounded `nudge`.

## Recommended next implementation step

Build the minimal habit-plan layer first:

1. onboarding-backed `category` + `habit plan` storage
2. habit-plan-aware extraction
3. due-habit evaluation
4. same-day fallback `check-in`

That is the shortest path from the current implementation to the product
behavior defined in `docs/PRODUCT.md`, `docs/CONTEXT.md`, and
`docs/ONBOARDING.md`.
