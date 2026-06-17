---
name: kaizen-milestone
description: "Write or refine a Kaizen milestone spec with a consistent template and checkable acceptance criteria. Use when the user wants to create a milestone, rewrite one for clarity, or verify that a milestone document is complete and well-structured."
---

# Kaizen Milestone

Use this skill to write milestone documents, tighten their structure, and make
their finish line checkable before implementation starts.

## Workflow

1. Read `AGENTS.md`, `docs/PRODUCT.md`, and the relevant file under
   `docs/milestones/`.
2. Write or rewrite the milestone so it has a clear:
   - objective
   - scope and constraints
   - acceptance criteria
   - test or verification expectations
3. Ensure every acceptance criterion is concrete enough to evaluate after
   implementation.
4. Normalize terminology to match the repo's product language.
5. Flag missing dependencies, sequencing assumptions, or vague requirements
   directly in the milestone doc.
6. Report what was clarified, what is still ambiguous, and whether the
   milestone is ready for implementation.

## Template Expectations

Make sure the milestone includes:

- a short statement of user-visible goal
- explicit non-goals where the boundary matters
- acceptance criteria that can be tested or inspected
- notes about migrations, config, evals, or frontend checks when relevant

## Guardrails

- Do not implement code from this skill; this skill prepares the milestone.
- Do not leave acceptance criteria at the level of "works" or "improve UX."
- Do not hide unresolved questions inside prose; call them out explicitly.
- Do not invent product behavior that conflicts with `docs/PRODUCT.md`.
