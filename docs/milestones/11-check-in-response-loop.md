# Milestone 11 - Check-in response loop

**Goal:** Close the fallback `check-in` loop so a user can answer Kaizen's
"did you complete this today?" prompt with `yes`, `partial`, or `no`, and have
that answer update trusted habit state instead of being stored as an unrelated
`log`.

**Unlocks:** usable same-day accountability. Fallback check-ins become a real
recovery path rather than a notification with no state-changing reply.

**Owner subagent:** `agent-engineer` with backend support for webhook routing,
effective evidence, XP recomputation, and dashboard visibility.

## Scope

In: detecting replies to the most recent open fallback `check-in`, resolving the
target habit or habits, writing append-only evidence overrides or equivalent
auditable check-in evidence, recomputing XP/progress idempotently, showing the
result in the read-only dashboard, and ensuring future fallback/proactive
decisions use the answered state.

Out: habit-plan creation or editing, dashboard input controls, arbitrary
multi-turn chat memory, freeform correction expansion beyond the existing
correction loop, and proactive nudge engagement analytics beyond marking the
check-in as answered if the data model needs it.

## Product decisions

- Telegram chat remains the only v1 surface for answering fallback `check-in`s.
- A bare `yes`, `partial`, or `no` should only be treated as a check-in answer
  when there is a recent unresolved fallback `check-in` for that user.
- If the latest unresolved check-in names exactly one habit, a bare answer is
  enough.
- If the latest unresolved check-in names multiple habits, Kaizen must ask one
  focused follow-up unless the answer explicitly names per-habit status.
- The original fallback `check-in` intervention remains auditable. The answer
  must not mutate or delete the intervention row.
- Check-in answers should feed the same effective habit-state path used by the
  dashboard, fallback checks, proactive decisions, and XP recomputation.

## User moments

- Single-habit recovery: Kaizen asks, "did you complete read today?" The user
  replies `yes`; today's `read` state becomes done, XP updates, and Kaizen
  confirms briefly.
- Partial completion: Kaizen asks about `gym`; the user replies `partial`; the
  state becomes partial and receives partial XP.
- Missed habit: Kaizen asks about `leetcode`; the user replies `no`; the state
  becomes missed, no XP is granted, and future ticks do not ask the same
  fallback check-in again that day.
- Multi-habit ambiguity: Kaizen asks about `gym` and `read`; the user replies
  `yes`; Kaizen asks which habit or requests a compact answer such as
  `gym yes, read no` instead of guessing.
- No open check-in: the user sends `yes` during ordinary logging; Kaizen treats
  it as a normal message or asks for clarification, but it must not create a
  check-in answer against stale state.

## Tasks

- [ ] Add a query for the latest unresolved fallback `check-in` intervention for
      the configured user and app-local day.
- [ ] Add a small Pydantic domain model for parsed check-in answers with
      statuses limited to `yes`, `partial`, and `no`.
- [ ] Route potential check-in answers before normal log persistence in
      `POST /webhook`, after command handling and before correction fallback.
- [ ] Resolve target habit/date from the open check-in reason/message and the
      current habit plan. Prefer structured data if the intervention model is
      extended; avoid parsing model free text when local metadata is available.
- [ ] Persist the answer as append-only auditable evidence using the existing
      effective-evidence override path or a new check-in evidence table if a
      migration is cleaner.
- [ ] Recompute XP/progress from effective state and return a concise Telegram
      confirmation, including XP delta when positive or negative.
- [ ] Ensure answered check-ins change dashboard habit status and recent
      intervention visibility without making the dashboard editable.
- [ ] Ensure later scheduler ticks for the same day do not ask the same fallback
      check-in again and proactive decisions see the answered state.
- [ ] Document the supported check-in reply syntax in `README.md`.

## Acceptance criteria

- When the latest unresolved check-in is for one due habit, replying `yes`
  creates auditable effective evidence for that habit/date, changes the
  dashboard status to `done`, recomputes XP, sends a confirmation, and does not
  insert a new `logs` row.
- Replying `partial` to a single-habit check-in changes the dashboard status to
  `done` or an explicitly represented partial state consistent with the
  existing dashboard vocabulary, awards partial XP, and remains visible as
  corrected or check-in-sourced evidence.
- Replying `no` to a single-habit check-in records the habit as missed for that
  date, grants no XP, prevents another fallback check-in for that habit/day, and
  leaves proactive decisions able to reason from the missed state.
- A bare `yes`, `partial`, or `no` with no unresolved same-day check-in is not
  applied to habit state and is not silently discarded.
- A bare answer to a multi-habit check-in asks one focused follow-up and creates
  no evidence until the habit-specific statuses are clear.
- Retrying the same check-in answer is idempotent for XP/progress even if a
  second audit row is written.
- The original `Intervention` row, the user's answer, and the effective habit
  state can all be inspected after the flow.
- Tests cover single-habit yes, partial, no, stale/no-open-check-in, multi-habit
  ambiguity, dashboard state, XP recomputation, and scheduler/proactive reuse of
  answered state.

## Verification

- `uv run pytest tests/test_webhook.py tests/test_dashboard.py tests/agent/test_proactive.py`
  passes, or a narrower equivalent slice is documented with the reason.
- `uv run ruff check .` is clean for Python changes.
- Manual Telegram smoke test: trigger a fallback check-in from
  `/scheduler/tick`, reply `yes`, open the dashboard, and verify the habit state
  and recent intervention history reflect the answer.

## Sequencing notes

This milestone should land before treating proactive nudges as production-ready
daily accountability. Without it, Kaizen can ask for missing evidence but cannot
learn from the answer in the same low-friction chat loop.
