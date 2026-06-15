# CONTEXT.md Format

## Structure

```md
# Kaizen Context

One or two sentences describing the part of Kaizen this glossary covers and why
it exists.

## Language

### Logging

**Log**:
A freeform Telegram message from the user describing a day, event, or check-in.
_Avoid_: Entry, note, update

**Habit**:
A behavior the user wants to build, maintain, or reduce.
_Avoid_: Goal, routine, task

**Trigger**:
A recurring situation or cue that makes a habit more or less likely.
_Avoid_: Cause, reason, signal

### Coaching

**Technique**:
A named behavioral-science method the agent can ground advice in.
_Avoid_: Tip, tactic, advice

**Nudge**:
A proactive message the agent sends when it believes intervention is useful.
_Avoid_: Alert, reminder, push

**Intervention**:
A nudge that the agent decides to deliver, records, and can later evaluate.
_Avoid_: Notification, message, ping

**Quiet hours**:
Times when the agent must stay silent unless an explicit override exists.
_Avoid_: Do-not-disturb, mute window
```

## Rules

- Be opinionated. Pick one canonical term and list alternatives under `_Avoid_`.
- Keep definitions tight. One or two sentences max. Define what it is, not how
  the system implements it.
- Only include terms that are specific to Kaizen's product or domain. General
  programming concepts do not belong here.
- Group terms under subheadings when the vocabulary naturally clusters.

## Single vs multi-context repos

Kaizen should default to a single project glossary in `docs/CONTEXT.md`.

If a `docs/CONTEXT-MAP.md` ever appears, use it to split terminology by
subsystem and follow the map before adding new terms.

If neither exists, create `docs/CONTEXT.md` lazily when the first term is
resolved.
```

## Notes

- Keep implementation details out of `docs/CONTEXT.md`.
- Prefer repo vocabulary from `AGENTS.md` and `docs/PRODUCT.md` when deciding
  the canonical term.
