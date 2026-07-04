# Bug: chat replies can ignore habit targets and cadence

Date: 2026-07-03 (DONE)

## Summary

Some ordinary chat replies behave as if the agent does not know the user's
habit targets, especially weekly cadence targets such as `3x/week`. This can
produce replies that imply the user needs to run or go to the gym today even
when the week has not ended and the target is not actually due yet.

## Observed behavior

Example reply:

> "On run/gym targets: You're right to clarify. Looking at your history, you're
> hitting gym (push/upper body) and runs consistently, but I don't see a written
> weekly target in your stated habits."

The response sounds like it is reasoning from history only, and it treats the
target as missing even though the habit plan stores cadence and goal metadata in
the database.

## Expected behavior

The agent should have access to the current habit plan when forming replies and
should respect cadence-aware targets.

For weekly habits:

- the agent should not imply a same-day requirement unless the habit is truly
  due today,
- the agent should recognize the stored cadence target from the habit plan,
- the reply should stay grounded in actual habit state, not just recent activity
  history.

## Likely cause

The ordinary user-message reply path does not pass habit-plan context into the
LLM prompt.

Current flow:

- `app/telegram/intake.py` routes normal logs to `run_user_message(...)`.
- `app/agent/graph.py` eventually calls `compose_log_reply(...)` for the reply.
- `compose_log_reply(...)` receives log text, extracted facts, retrieved lesson
  chunks, and memory history, but not the habit plan or due-habit summary.

The backend does read the habit plan in other places, including extraction and
proactive scheduling, so the data exists. The issue is that this specific reply
path is not consistently given that context.

## Impact

- Misleading coaching language.
- Confusion about whether weekly targets are being tracked correctly.
- Lower trust in habit-state reasoning, especially for `times_per_week` habits.

## Suggested fix

Add cadence-aware habit-plan context or a compact due/not-due summary to the
ordinary reply prompt, or route these replies through a grounded habit-state
read model before generation.

The fix should ensure the model sees:

- the current habit plan,
- cadence type/value,
- whether the habit is currently due,
- and any relevant recent completion evidence.

## Acceptance criteria

- A reply about run/gym habits reflects the stored weekly target when present.
- A `3x/week` habit does not get described as needing completion today unless
  the due-habit logic actually marks it due.
- Regression tests cover the reply path for a weekly habit with remaining days
  in the week.

