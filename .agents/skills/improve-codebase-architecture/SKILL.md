---
name: improve-codebase-architecture
description: Find Kaizen architecture deepening opportunities that reduce AI-spaghetti risk, present them as a visual HTML report, then route the chosen candidate through grill-with-docs. Use when reviewing Kaizen code structure, module boundaries, testability, long-term maintainability, or before implementing a milestone that may spread logic across backend, agent, RAG, frontend, or docs.
---

# Improve Codebase Architecture

Surface architectural friction in Kaizen and propose deepening opportunities:
refactors that move scattered behavior behind a small, useful interface. The aim
is to prevent AI-generated spaghetti by improving locality, leverage, and
testability before implementation work expands.

## Vocabulary

Use these architecture terms consistently: `module`, `interface`,
`implementation`, `deep`, `shallow`, `seam`, `adapter`, `locality`, and
`leverage`.

Definitions: a deep module has a small interface and substantial useful
implementation; a shallow module exposes nearly as much complexity as it hides;
a seam is a real split where dependencies or tests can substitute behavior; an
adapter translates across a seam; locality keeps related behavior together;
leverage means one interface improves many call sites or tests.

Use Kaizen domain language from `docs/CONTEXT.md`: logs, habits, techniques, nudges, interventions, quiet hours, grounded replies, memory, and check-ins.

## Process

### 1. Read context

Read first: `AGENTS.md`, `docs/PRODUCT.md`, `docs/CONTEXT.md`, relevant milestone specs under `docs/milestones/`, relevant notes under `docs/review/`, and existing ADRs under `docs/adr/`, if present.

Then read the area skill that matches the code being reviewed:

- `kaizen-backend` for FastAPI, Telegram, DB, config, and the LLM gateway
- `kaizen-agent` for LangGraph, memory, scheduler, and proactive logic
- `kaizen-rag` for corpus, embeddings, retrieval, reranking, and grounded replies
- `kaizen-evals` for evals, judge rubrics, reports, and Langfuse
- `kaizen-frontend` for the Telegram Mini App and `/miniapp` glue

### 2. Explore code

Inspect code and tests directly. Use subagents only if the user explicitly asked for delegated or parallel agent work.

Look for friction:

- One Kaizen concept requires bouncing across many files.
- A module is shallow: callers know too much about its implementation.
- Milestone behavior spreads across webhook, agent, memory, RAG, and tests with
  no stable interface.
- Tests reach through internals instead of exercising a meaningful interface.
- The LLM gateway, Telegram allowlist, structured extraction, memory payloads,
  RAG grounding, quiet hours, or intervention recording are bypassable.
- A seam exists for only one adapter and creates indirection without leverage.

Apply the deletion test to suspected shallow modules: if deleting the module
concentrates behavior and simplifies tests, it is probably shallow.

### 3. Present candidates

Write a self-contained HTML file to the OS temp directory so nothing lands in
the repo. Resolve the temp dir from `$TMPDIR`, falling back to `/tmp` or `%TEMP%`,
and write to `<tmpdir>/kaizen-architecture-review-<timestamp>.html`. Open it for
the user if allowed by the current environment and report the absolute path.

Use Tailwind via CDN and Mermaid via CDN. Mix Mermaid with hand-built CSS/SVG.
Every candidate must have a before/after visualization.

Each candidate card includes:

- Files and modules involved
- Problem and solution, without implementing yet
- Benefits in locality, leverage, and tests
- Before/after diagram
- Recommendation strength: `Strong`, `Worth exploring`, or `Speculative`
- Relevant milestone or doc anchor, when one applies

End with a top recommendation and why it should be handled first.

See [HTML-REPORT.md](HTML-REPORT.md) for the scaffold, diagram patterns, and
styling guidance.

Do not implement or finalize a new interface during the report. After the file is
written, ask: "Which candidate do you want to grill first?"

### 4. Grilling loop

Once the user picks a candidate, use `grill-with-docs` to pressure-test it
against product intent, milestone docs, code, and terminology.

During the grilling loop:

- Ask one question at a time and include a recommended answer.
- Update `docs/CONTEXT.md` when a settled term or Kaizen concept changes.
- Create an ADR only for hard-to-reverse, surprising trade-offs.
- Route implementation to the relevant Kaizen area skill after the design is
  settled.

The final output of the grilling loop should be either a scoped implementation
plan or a documented reason to reject the refactor.
