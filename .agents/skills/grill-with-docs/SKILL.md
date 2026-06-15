---
name: grill-with-docs
description: "Stress-test a Kaizen plan against product intent, milestone docs, code, and terminology; update docs inline as decisions crystallise."
---

# Grill With Docs

Use this skill when a proposal needs pressure-testing against Kaizen's product
intent, existing code, and documented decisions.

## Read first

1. `AGENTS.md`
2. `docs/PRODUCT.md`
3. The relevant milestone spec under `docs/milestones/`
4. The touched code and tests
5. Existing docs that cover the same area

## Workflow

1. Resolve the user's actual goal in Kaizen terms before discussing design.
2. Read the codebase before asking anything the code can answer.
3. Ask one question at a time, and include a recommended answer.
4. Challenge fuzzy, overloaded, or conflicting terms immediately.
5. Use concrete scenarios to force boundary decisions when the shape is unclear.
6. Update docs as soon as a term or decision is settled.
7. Create an ADR only when the decision is hard to reverse, surprising, and a
   real trade-off.

## Doc targets

- Use `docs/CONTEXT.md` for canonical terminology and glossary entries.
- Use `docs/adr/NNNN-slug.md` for durable decisions and trade-offs.
- Create either lazily, only when there is something worth writing.
- If `docs/CONTEXT-MAP.md` ever appears, use it to route terminology by
  context.

## Kaizen terminology

Prefer the repo's language over generic alternatives.

- `log` for a user's freeform Telegram message
- `habit` for a tracked behavior the user wants to build or break
- `technique` for a grounded behavioral-science method
- `nudge` for a proactive message sent by the agent
- `intervention` for a nudge that is intentionally delivered, recorded, and
  reviewed
- `quiet hours` for times when proactive messages must stay silent
- `grounded` for advice tied to a real technique and the user's own history

## Output discipline

- Keep the conversation focused on resolving one branch of the design tree at a
  time.
- If the code already answers the question, surface that instead of debating it.
- Do not write implementation details into `docs/CONTEXT.md`.
- Do not batch terminology updates if a term is already settled.
