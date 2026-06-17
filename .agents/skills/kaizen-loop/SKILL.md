---
name: kaizen-loop
description: "Run a Kaizen implementation loop that starts from a written milestone, routes work to the right repo skills, and checks the result against the milestone. Use when the user wants to execute milestone-driven work with GPT-5.5 for planning and review and GPT-5.4 for implementation."
---

# Kaizen Loop

Use this skill to orchestrate milestone-driven work across the repo's narrower
skills.

The loop has three explicit phases:

1. `GPT-5.5 planning`: confirm the milestone and the checkable finish line.
2. `GPT-5.4 implementation`: hand work packets to the necessary domain skills.
3. `GPT-5.5 review`: run checks and decide whether another loop is needed.

Use `$kaizen-milestone` first to ensure the milestone is written clearly and
uses a consistent template. Use `$grill-with-docs` during planning and review
so the loop stays grounded in product intent, milestone docs, touched code, and
repo terminology.

## Workflow

1. Start with `$kaizen-milestone` to confirm the milestone is implementation
   ready.
2. Use `$grill-with-docs` to pressure-test the milestone against
   `AGENTS.md`, `docs/PRODUCT.md`, the relevant milestone spec, and the current
   code.
3. Break the milestone into small work packets with:
   - packet goal
   - likely files or modules
   - expected output
   - verification step
4. Route each packet to the necessary skill:
   - API, config, database, migrations, webhook, LLM gateway: `$kaizen-backend`
   - LangGraph, memory, scheduler, proactive logic: `$kaizen-agent`
   - retrieval, embeddings, corpus, reranking: `$kaizen-rag`
   - Telegram Mini App and `/miniapp` glue: `$kaizen-frontend`
   - evals, reports, judge rubrics, tracing: `$kaizen-evals`
5. Hand the implementation packets to `GPT-5.4`.
6. Reassemble the outputs and run the planned checks.
7. Use `$grill-with-docs` again to review the result against the milestone and
   decide `done`, `needs another loop`, or `blocked`.

## Output Shape

Always keep these sections explicit:

- `Milestone`
- `Work packets`
- `Skill routing`
- `Checks`
- `Decision`

## Guardrails

- Do not start implementation before `$kaizen-milestone` confirms the
  milestone is concrete enough to execute.
- Do not skip `$grill-with-docs` for planning or review.
- Do not distribute vague packets; each packet needs an artifact and a check.
- Do not use a domain skill unless the packet actually touches that area.
- Do not mark work done without running or explicitly accounting for the
  planned checks.

## Minimal Template

```md
Milestone
- Objective:
- Constraints:
- Acceptance criteria:
- Checks:

Work packets
- Packet 1:
- Packet 2:

Skill routing
- Packet 1 -> $skill-name
- Packet 2 -> $skill-name

Checks
- Planned:
- Ran:

Decision
- done | needs another loop | blocked
```
