---
name: kaizen-milestone
description: "Implement or verify a Kaizen milestone from docs/milestones. Use when the user asks to work through a milestone, satisfy acceptance criteria, or decide what remains for a milestone."
---

# Kaizen Milestone

Use this skill to drive milestone work from specification to verification.

## Workflow

1. Read `AGENTS.md`, `docs/PRODUCT.md`, and the relevant file under
   `docs/milestones/`.
2. Identify the acceptance criteria and map each one to an existing or needed
   test.
3. Inspect the current implementation before editing. Prefer existing patterns
   over new abstractions.
4. Make the smallest implementation that satisfies the criteria.
5. Run focused tests first, then broader checks when risk justifies it.
6. Report which acceptance criteria are met, which checks ran, and any remaining
   gaps.

## Milestone Routing

- Skeleton/webhook/config/database work: use `$kaizen-backend`.
- Extraction through the LLM gateway: use `$kaizen-backend`.
- RAG, corpus, embeddings, retrieval, and reranking: use `$kaizen-rag`.
- Gamification and stats: start from existing app/test structure; use
  `$kaizen-backend` if API or database work is involved.
- Memory, LangGraph, scheduler, and proactive nudges: use `$kaizen-agent`.
- Evals, reports, judge rubrics, and tracing: use `$kaizen-evals`.
- Telegram Mini App UI: use `$kaizen-frontend`.

## Guardrails

- Do not mark a milestone done without tests for its acceptance criteria.
- Do not bypass `app/llm/client.py` for model or embedding calls.
- Do not fake measured metrics. If a metric is not measured, say so.
- Do not add services or third-party calls beyond the project rules without
  flagging the privacy impact.
