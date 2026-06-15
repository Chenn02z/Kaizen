# Kaizen V1 Onboarding Spec

This document defines the minimum onboarding output Kaizen needs before the
agent can provide real accountability.

## Purpose

Kaizen should not reason only over raw `log`s. It needs an explicit `habit
plan` so it can answer three questions reliably:

1. Which `habit`s exist?
2. Which `habit`s were due today?
3. Does today's `log` contain enough evidence to count the habit as done?

The onboarding surface can stay simple in v1. What matters is that it produces
the habit-plan data below.

## V1 outputs

Onboarding creates:

- one or more `category` records
- one or more `habit plan` records linked to a category

`category` is organizational only. `habit` remains the operational unit for
matching, missed-day detection, fallback `check-in`s, and proactive `nudge`s.

## Habit plan schema

Each `habit` in v1 should capture:

- `category_name`
- `habit_name`
- `direction`
  - `build` or `break`
- `cadence_type`
  - one of `daily`, `specific_weekdays`, `times_per_week`
- `cadence_value`
  - for `daily`: no extra value
  - for `specific_weekdays`: a list like `["mon", "wed", "fri"]`
  - for `times_per_week`: an integer target like `3`
- `success_condition`
  - a concrete description of what counts as success from a natural-language
    `log`
- `habit_aliases`
  - a short list of phrases or examples that help map free text onto the habit
- `known_triggers`
  - optional; user-known contexts that make success or failure more likely
- `goal`
  - optional; why the habit exists
- `fallback_checkin_enabled`
  - boolean, default `true`
- `expected_evidence_window`
  - optional in v1; if omitted, Kaizen can use a simple default before the
    end of the day when deciding whether to send a fallback `check-in`

## Matching rules

These rules are part of the product shape, not optional implementation details.

- Kaizen should infer adherence from natural-language `log`s by default.
- One `log` may satisfy multiple `habit`s when it contains clear evidence for
  each one.
- `habit_aliases` are soft anchors for extraction, not exact-match keys.
- `success_condition` should be concrete enough to judge from a `log`, but broad
  enough to capture real progress.
- When matching is ambiguous, Kaizen should prefer precision over recall:
  leave the habit unmatched rather than over-crediting it.
- If a due `habit` remains unmatched by its `expected_evidence_window`, Kaizen
  may send one same-day fallback `check-in`.

## Seed habit plan

The initial v1 seed discussed so far is:

| Category | Habit | Direction | Cadence | Success condition | Example aliases / evidence |
|---|---|---|---|---|---|
| `FITNESS` | `run` | `build` | `times_per_week` | Completed a real run session | `ran`, `went for a run`, `5k`, `jogged` |
| `FITNESS` | `gym` | `build` | `times_per_week` | Completed a gym workout session | `gym`, `lifted`, `workout`, `trained chest` |
| `CAREER` | `leetcode` | `build` | `daily` | Solved or seriously attempted at least one Leetcode session | `leetcode`, `did one problem`, `solved two mediums`, `practiced DSA` |
| `CAREER` | `personal project` | `build` | `times_per_week` | Made meaningful progress on a personal project | `started a new project`, `built a feature`, `shipped a fix`, `worked on the app` |
| `SELF` | `read` | `build` | `daily` | Completed a real reading session | `read 20 pages`, `finished a chapter`, `kept reading`, `read before bed` |

For `times_per_week` habits, the exact integer target is still a user-specific
input captured during onboarding.

## What v1 does not need

- nested category systems
- arbitrary recurrence rules
- separate per-habit scoring formulas
- perfect semantic matching
- a mandatory checklist workflow for every day

## Milestone implications

- Milestone 2 should treat extraction as matching free-text evidence onto known
  `habit`s from the habit plan, not just producing generic habit strings.
- Milestone 5 should evaluate due habits against cadence and support one
  same-day fallback `check-in` before escalating to a proactive `nudge`.
