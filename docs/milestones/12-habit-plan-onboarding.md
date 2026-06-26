# Milestone 12 - Telegram habit-plan onboarding

**Goal:** Let the user review, add, and edit tracked `habit`s and `category`
assignments from Telegram through a structured command flow, so Kaizen can adapt
to new goals without code or manual database edits.

**Unlocks:** real daily use as the user's habits change. Resume keywords
Telegram command UX, habit-plan onboarding, structured state management, product
operations.

**Owner subagent:** `backend-engineer` with light frontend support only if the
read-only dashboard needs additional fields to reflect edited habit plans.

## Scope

In: `/habits`, `/habit_add`, and `/habit_edit` command handling; a structured
Telegram wizard for habit creation and editing; validation for v1 cadence
patterns; updates to the existing `habit_categories` and `habit_plans` source of
truth; dashboard read-model visibility for the resulting plan; tests that prove
commands are not stored as ordinary `log`s.

Out: pause/resume, delete/archive flows, habit-plan editing inside the Mini App,
AI-generated habit suggestions, multi-user plan management, expected-window
configuration by the user, social features, and arbitrary natural-language
habit-plan mutation outside the supported commands.

## Prerequisites

Milestones 1, 2, 6, 8, and 11. The command flow relies on persisted logs,
structured extraction against the current `habit plan`, due-habit logic, the
read-only dashboard, and check-in answers sharing the same effective habit-state
path.

## Product decisions

- Telegram chat is the v1 write surface for habit-plan onboarding.
- The `dashboard` remains read-only. It may reveal updated habit-plan state, but
  it must not create or edit plans.
- Habit onboarding is structured and deterministic. The first implementation
  should not use an LLM to infer habit definitions from free text.
- `/habits` is the user's lightweight command for inspecting the current plan in
  chat without opening the Mini App.
- `/habit_add` collects one habit at a time: habit name, category, cadence,
  success condition, and aliases/examples.
- `/habit_edit <habit>` edits one existing habit at a time and exposes only the
  fields needed for v1: name, category, cadence, success condition, and aliases.
- Expected evidence windows remain an internal default for fallback check-ins in
  this milestone. The user should not be asked to configure one during habit
  onboarding.
- Commands with bot suffixes, such as `/habit_add@KaizenBot`, should behave the
  same as unsuffixed commands.

## User moments

- Review current plan: the user sends `/habits` and receives a grouped list of
  active habits with category, cadence, success condition, and aliases.
- Add a new habit: the user sends `/habit_add`; Kaizen asks a short sequence of
  questions and then shows a confirmation summary before writing the new habit.
- Create a new category during add: when the category step cannot match an
  existing category, Kaizen lets the user explicitly confirm a new category
  instead of silently creating one from a typo.
- Edit a habit: the user sends `/habit_edit gym`; Kaizen shows editable fields,
  accepts one field update at a time, and confirms the final saved definition.
- Cancel safely: the user sends `cancel` during an add/edit flow; no partial
  habit-plan change is persisted and the message is not stored as a `log`.

## Command UX

`/habits` should return a compact chat summary grouped by `category`, for
example:

```text
FITNESS
- gym: 3x/week - Completed a gym workout session
  aliases: gym, lifted, workout

CAREER
- leetcode: daily - Solved or seriously attempted at least one Leetcode session
  aliases: leetcode, did one problem, practiced DSA
```

`/habit_add` should run a structured flow:

```text
Habit name?
Category? Choose an existing category or type a new one.
Cadence? daily, weekdays, or N times per week.
What counts as success?
Aliases/examples? Send comma-separated examples or "skip".
Confirm this habit? yes/no
```

`/habit_edit <habit>` should resolve the target habit using exact name first and
then aliases only when there is one unambiguous match. If multiple habits could
match, Kaizen should ask one focused follow-up instead of guessing.

## Data model notes

- Final habit-plan state should continue to live in `habit_categories` and
  `habit_plans`; do not introduce a second source of truth.
- If the structured wizard spans multiple Telegram messages, pending add/edit
  state must be durable enough for normal app restarts. Prefer a small
  append-only or replaceable pending-command table over process-local memory.
- New habits should use the existing internal default for
  `expected_evidence_window` so fallback check-ins keep working without adding a
  user-facing setup step.
- Habit names remain unique per Telegram user. Renaming a habit must account for
  existing progress/evidence references or explicitly document any v1 limitation
  before implementation.

## Tasks

- [ ] Add command routing for `/habits`, `/habit_add`, and `/habit_edit` before
      normal log persistence, correction handling, and check-in answer handling
      where appropriate.
- [ ] Add Pydantic domain models for habit-plan command state, accepted cadence
      values, and validated habit updates.
- [ ] Add durable pending-flow storage if the wizard requires multiple Telegram
      messages; include an Alembic migration if a new table is used.
- [ ] Implement `/habits` as a read-only plan summary grouped by category.
- [ ] Implement `/habit_add` as a structured flow with validation, summary, and
      explicit confirmation before inserting rows.
- [ ] Implement `/habit_edit <habit>` as a structured flow with unambiguous
      habit resolution and field-level validation before saving updates.
- [ ] Ensure added/edited plans are used immediately by extraction prompts,
      fallback check-ins, proactive decisions, XP/progress recomputation, and
      the dashboard read model.
- [ ] Preserve the existing `/start`, `/dashboard`, and `/app` dashboard launch
      behavior.
- [ ] Document supported commands and examples in `README.md`.

## Acceptance criteria

- Sending `/habits` from the allowed Telegram user returns the current habit plan
  grouped by category and does not insert a `logs` row.
- Sending `/habit_add` starts a structured flow that collects habit name,
  category, cadence, success condition, aliases/examples, and explicit
  confirmation before creating a `habit_plans` row.
- Adding a habit with an existing category reuses that `habit_categories` row;
  adding with a confirmed new category creates exactly one new category row.
- Added habits support only v1 cadence patterns: `daily`, `specific weekdays`,
  and `N times per week`; invalid cadence input asks for correction without
  writing a partial habit.
- Added habits appear in `/habits`, the dashboard read model, and the extraction
  habit-plan prompt used for later logs.
- Sending `/habit_edit <habit>` updates only the selected existing habit after
  explicit confirmation and does not create duplicate habit names.
- Editing aliases changes the extraction prompt context for later logs without
  mutating old `logs` or `extracted_facts` rows.
- Ambiguous edit targets produce one focused follow-up and make no database
  change until the target habit is clear.
- Sending `cancel` during add/edit clears the pending flow, writes no
  habit-plan change, and does not store the message as a `log`.
- Unsupported commands such as `/habit_delete`, `/habit_pause`, or
  `/habit_resume` receive a clear unsupported-command response and do not mutate
  habit-plan state.
- Existing `/start`, `/dashboard`, and `/app` behavior remains unchanged and
  continues to skip log insertion.
- Tests cover command routing, add happy path, edit happy path, invalid cadence,
  ambiguous edit target, cancel, dashboard visibility, extraction-context
  visibility, and unsupported commands.

## Verification

- `uv run pytest tests/test_webhook.py tests/habits tests/test_dashboard.py`
  passes, or a narrower equivalent slice is documented with the reason.
- `uv run ruff check .` is clean for Python changes.
- If a migration is added, `uv run alembic upgrade head` succeeds.
- Manual Telegram smoke test: add one new habit, edit its aliases, send a later
  log using one alias, open the dashboard, and verify the habit appears and can
  receive evidence.

## Sequencing notes

This milestone should land before relying on Kaizen for long-running real habit
change. Without it, the habit plan drifts behind the user's actual goals, which
weakens extraction, fallback check-ins, proactive decisions, and dashboard trust.

## Open questions

- Renaming habits may require a compatibility decision because existing
  `extracted_facts`, evidence overrides, and progress rows currently reference
  habit names. The implementation should either migrate those references during
  rename or limit v1 editing to non-name fields.
- The exact Telegram UI mechanics can be plain text prompts first. Inline
  keyboards are optional unless they materially reduce ambiguity in the flow.
