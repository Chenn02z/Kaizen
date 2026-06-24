---
name: kaizen-product-review
description: "Orchestrate Kaizen product reviews from a product manager and user perspective, then turn concrete findings into milestone specs. Use when the user asks to review what Kaizen currently does, assess user experience, find product gaps, prioritize feedback, or create new milestones from product observations."
---

# Kaizen Product Review

Use this skill to inspect Kaizen as a product rather than as an implementation
task. The goal is to understand what the product currently does, evaluate it
from the builder-user's perspective, give concrete feedback, and create
implementation-ready milestones through `$kaizen-milestone`.

This is not the same as `$kaizen-loop`: do not start from an existing milestone
or route implementation packets. Start from the current product experience.

## Review Loop

1. `Product discovery`: read product intent, docs, and visible behavior.
2. `User walkthrough`: trace what the user can actually do today.
3. `PM critique`: identify concrete product gaps and priorities.
4. `Milestone creation`: use `$kaizen-milestone` for selected feedback.

Use `$grill-with-docs` when product terms, intent, or trade-offs need pressure
testing against `AGENTS.md`, `docs/PRODUCT.md`, current milestone docs, and
code. Use `$kaizen-milestone` only after the review has selected a concrete
product opportunity to specify.

## Workflow

1. Read `AGENTS.md`, `docs/PRODUCT.md`, `docs/CONTEXT.md` if present, and the
   current milestone index under `docs/milestones/`.
2. Inspect the shipped surface area relevant to the review:
   Telegram flows, reflection, extraction, memory, RAG, proactive ticks,
   corrections, Mini App dashboard, evals, and observability.
3. Build a current-product map:
   what the user can do, what Kaizen does in response, what data is stored or
   recalled, and what feedback loop is visible.
4. Walk through 3-5 realistic user scenarios from the target user's perspective.
   Include happy paths, recovery paths, and moments where Kaizen should stay
   silent.
5. Give concrete PM feedback:
   user-visible problem, product impact, evidence, severity, priority, and the
   smallest milestone-shaped next step.
6. Ask the user which feedback item to turn into a milestone if priority is not
   obvious. If it is obvious, state the assumption and proceed.
7. Use `$kaizen-milestone` to write or update the milestone in
   `docs/milestones/` with clear scope, non-goals, acceptance criteria, and
   verification expectations.

## Output Shape

Always keep these sections explicit:

- `Current product`
- `User walkthroughs`
- `Feedback`
- `Milestone candidates`
- `Created milestones`
- `Decision`

## Guardrails

- Do not implement product changes from this skill. Create feedback and
  milestone specs only.
- Do not give vague feedback like "improve onboarding" without a specific user
  moment, reason, and milestone-shaped next step.
- Do not invent product behavior that conflicts with `docs/PRODUCT.md`.
- Do not judge the product only from code internals. Tie findings to user
  experience and the product promise.
- Do not create a milestone until the problem, target user behavior, and
  acceptance criteria are concrete enough for `$kaizen-milestone`.
- Prefer fewer, sharper milestones over a large backlog dump.

## Minimal Template

```md
Current product
- What exists / coverage / gaps:

User walkthroughs
- Scenario 1:
- Scenario 2:

Feedback
- Finding / evidence / severity / next step:

Milestone candidates
- Candidate 1:
- Candidate 2:

Created milestones
- Path / objective / acceptance criteria:

Decision
- milestone created | needs user priority choice | blocked
```
