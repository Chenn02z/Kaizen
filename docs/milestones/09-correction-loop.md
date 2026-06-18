# Milestone 9 - Correction loop

**Goal:** Let the user repair Kaizen's interpretation in Telegram when
extraction is wrong, incomplete, or too conservative.

**Unlocks:** trust in the habit state; resume keywords human-in-the-loop AI,
auditable overrides, state reconciliation.

**Owner subagent:** `backend-engineer` with agent support for natural-language
correction routing.

## Scope

In: chat-based correction intents, an auditable evidence override model,
habit-state recomputation that applies overrides, XP adjustment when corrected
state changes adherence, and dashboard visibility for corrected evidence.

Out: dashboard editing, multi-user review workflows, habit-plan creation or
editing, and full conversation undo beyond habit evidence corrections.

## Prerequisites

Milestones 1, 2, 4, and 8. This should be completed before treating Milestone 6
proactive decisions as production-ready, because nudges depend on trusted habit
state.

## Product decisions

- Telegram chat is the v1 correction surface.
- The dashboard remains read-only, but it should reveal when habit state includes
  a user correction.
- Corrections are append-only audit records. Do not mutate or delete the
  original `log` or original `extracted_facts` row when correcting it.
- Corrections override habit-state computation for the targeted habit/date, but
  the original model output remains inspectable for debugging and evals.
- If a correction cannot be resolved confidently, Kaizen asks one focused
  follow-up question instead of guessing.

## Correction intents

Support explicit correction phrases first:

- `count that as gym`
- `count my last log as partial for gym`
- `undo gym credit for today`
- `mark sleep as missed`
- `that was not a workout`
- `do not use that as evidence next time`

The first implementation can use a small structured parser backed by the LLM
gateway when needed, but the output must be a Pydantic model and all model calls
must go through `app/llm/client.py`.

## Data model

Add an append-only correction table, for example `habit_evidence_overrides`:

- `id`
- `telegram_user_id`
- `log_id` nullable
- `habit_name`
- `target_date`
- `override_status`: `yes`, `partial`, `no`, or `unmatched`
- `user_text`
- `reason`
- `created_at`

Use Alembic for the schema change. Keep habit identifiers aligned with the
existing habit-plan source of truth.

## Tasks

- [ ] Add the correction schema/model, migration, and Pydantic domain types.
- [ ] Add correction-intent detection before normal log persistence when a
      message is clearly a correction.
- [ ] Resolve target habit/date/log using recent logs, known habits, and the
      user's text; ask a follow-up when resolution is ambiguous.
- [ ] Apply overrides in the shared habit-state read path used by the dashboard,
      fallback check-ins, and proactive agent inputs.
- [ ] Adjust XP/progress idempotently when a correction changes the effective
      adherence state.
- [ ] Show corrected state in the dashboard read model without making the
      dashboard editable.
- [ ] Add eval fixtures for false positive, false negative, partial-credit, and
      ambiguous correction cases.

## Acceptance criteria (verify each)

- A false negative can be repaired: after `count that as gym`, today's gym state
  changes from missing/unknown to done or partial in the backend read model.
- A false positive can be repaired: after `that was not a workout`, the habit no
  longer counts as complete for the target date.
- Corrections are auditable: the original `log`, original `extracted_facts`, and
  correction row can all be inspected.
- Ambiguous corrections produce a follow-up question and do not create an
  override row until the target habit/date/log is clear.
- XP/progress changes are idempotent when the same correction flow is retried.
- Fallback check-ins and proactive decisions use corrected habit state.
- `uv run pytest tests/habits tests/test_dashboard.py tests/test_webhook.py`
  passes, or a narrower equivalent test slice is documented with the reason.

## Definition of done

Acceptance criteria are covered by tests, `uv run ruff check .` is clean for
Python changes, and the correction path is documented in the README or a product
doc that the user can find before daily use.

## Resume bullet unlocked

Built a human-in-the-loop correction system for habit evidence, preserving
model outputs while applying auditable user overrides to habit state and
progress.
