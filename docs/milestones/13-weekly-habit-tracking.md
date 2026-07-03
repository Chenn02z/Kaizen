# Milestone 13 - Weekly habit tracking and XP decision

**Goal:** Replace the dashboard's XP-first progress framing with a simple weekly
habit evidence view: each `habit` shows seven weekday markers, such as `M T W T
F S S`, with a clear visual difference between days that are done and days that
are not done.

**Unlocks:** a calmer progress surface that matches how the user thinks about
habit consistency, and a deliberate product decision on whether XP should be
removed completely before more RAG work expands Kaizen's coaching depth.

**Owner subagent:** `frontend-engineer` with backend support.

## Scope

In: a dashboard read-model change for per-habit weekly completion state, a Mini
App redesign that makes weekly habit evidence the primary progress display, an
audit of every XP/level surface, and an explicit decision to remove, hide, or
retain XP with rationale.

Out: habit-plan editing, arbitrary analytics charts, social streaks,
leaderboards, rewards, wearable integrations, calendar sync, and changes to
RAG, memory, or proactive nudge policy.

## Prerequisites

Milestones 8, 9, 11, and 12 should exist before implementation, because weekly
status must be derived from the same effective habit state used by corrections,
check-in answers, fallback checks, proactive decisions, and habit-plan cadence.

This milestone should land before Milestone 14 corpus expansion. Corpus work
deepens Kaizen's advice; this milestone clarifies the product surface that
advice is supporting.

## Product decisions

- The dashboard should foreground observable `habit` evidence, not abstract
  game points.
- The primary progress unit is a habit-day: whether Kaizen has effective
  evidence that a habit was done on a specific local calendar day.
- The weekly row uses stable weekday labels ordered Monday through Sunday:
  `M T W T F S S`.
- A done day and not-done day must be visually distinct without relying only on
  color. For example, done may use a filled circle with an accessible label;
  not done may use an outlined or muted circle.
- The first implementation should use the current Monday-through-Sunday
  calendar week in the user's configured timezone, not a month heatmap.
- `partial` evidence is not a third primary visual state unless the
  implementation proves it is necessary. If retained, it must stay secondary to
  the done/not-done distinction.
- XP and levels are under review. The default hypothesis is that XP should be
  removed from the user-facing product because it competes with Kaizen's core
  accountability loop: log, understand, reflect, intervene.

## XP removal decision

Start implementation with a short XP audit. The output should classify every
XP/level dependency as one of:

- User-facing display: Mini App text, bot replies, `/me`, dashboard JSON, docs,
  screenshots, or resume copy.
- Derived progress infrastructure: `user_progress`, `habit_progress`, XP
  recomputation, tests, and correction/check-in side effects.
- Compatibility surface: endpoints or schemas that existing tests or clients
  still call.

Then choose one path and record the rationale in this milestone or a short
adjacent note:

- **Remove XP completely:** delete XP/level display, stop awarding or
  recomputing XP, remove XP from dashboard contracts, and migrate/drop progress
  columns or tables when safe.
- **Deprecate XP internally:** remove XP/level from the product UX and new
  dashboard contracts, but leave historical tables or `/me` compatibility in
  place until a later cleanup migration.
- **Retain XP as secondary:** keep XP only if the audit identifies a concrete
  use that weekly habit evidence does not cover. If this path is chosen, XP must
  not be the first-screen dashboard hierarchy.

The recommended path is **deprecate XP internally** unless the code audit shows
that complete removal is low-risk. This keeps the user experience focused while
avoiding a schema cleanup milestone hidden inside a dashboard redesign.

**Decision:** deprecate XP internally. The audit found user-facing XP in the
Mini App dashboard hierarchy, dashboard JSON, bot/check-in/correction copy, and
tests. It also found derived progress infrastructure in `user_progress`,
`habit_progress`, XP recomputation from effective evidence, habit rename
compatibility, and `/me` stats. This milestone removes XP/level from
`/dashboard`, the Mini App, and bot-facing progress copy, while leaving
`user_progress`, `habit_progress`, recomputation, and `/me` in place as
compatibility surfaces. A later cleanup can remove those tables and the
gamification module if no client or test still depends on `/me`.

## Weekly dashboard behavior

For each active `habit`, the dashboard should show:

- habit name and category
- cadence summary, such as `daily`, `Mon/Wed/Fri`, or `3x/week`
- seven weekday markers for the current local week, Monday through Sunday
- each marker's date, weekday, and status in accessible metadata or tooltip text
- a compact current-week count, such as `3/5 days` for a weekday-specific
  target or `2/3 this week` for an N-times-per-week target
- today's status using the existing dashboard vocabulary where useful: `done`,
  `missing`, `not_due`, or `unknown`

The read model must derive this from persisted `log`s, `extracted_facts`,
`habit_plans`, and `evidence override`s. React should render the state it is
given, not infer whether a habit was done.

## Tasks

- [x] Audit all XP/level references in backend models, read models, Telegram
      replies, Mini App code, tests, docs, and migrations.
- [x] Record the XP decision path: remove completely, deprecate internally, or
      retain as secondary, with a concrete rationale and cleanup boundaries.
- [x] Add a typed backend weekly habit read model that returns seven local-date
      status entries per active habit.
- [x] Ensure weekly status uses effective habit state, including extraction
      results, check-in answers, and evidence overrides.
- [x] Update the dashboard API contract so the Mini App can render weekly habit
      rows without frontend-only inference.
- [x] Redesign the `Habits` or `Today` dashboard section around weekday circle
      markers, with stable sizing on mobile and desktop Telegram WebViews.
- [x] Remove XP/level from the first-screen dashboard hierarchy. If XP is kept
      at all, move it behind the weekly evidence view and document why.
- [x] Update Telegram reply copy if it currently reports XP gain after every
      log, so successful logs confirm interpreted habit evidence instead.
- [x] Update tests that currently assert XP-driven dashboard or reply behavior
      to assert weekly evidence and effective-state behavior instead.
- [x] Update product docs or milestone notes so future work does not re-expand
      XP as a primary motivation system by accident.

## Acceptance criteria

- The dashboard read model returns, for each active habit, exactly seven
  current-week day entries ordered Monday through Sunday in the configured
  timezone.
- A fixture with a `leetcode` habit and evidence on Monday, Wednesday, and
  Saturday renders or serializes those three days as done and the other weekday
  markers as `missing`, `not_due`, or `unknown` according to cadence and date.
- Weekly day status is derived from effective habit state, so a correction or
  check-in answer changes the appropriate day marker without changing the
  original log row.
- N-times-per-week cadence shows a current-week completion count against the
  target, while specific-weekday cadence still shows all seven markers.
- The Mini App renders each habit with weekday markers labeled `M T W T F S S`,
  and done/not-done states are visually distinguishable without relying only on
  color.
- XP/level no longer controls the dashboard's primary information architecture.
- The XP audit result is documented and one of the three decision paths is
  explicitly chosen.
- If XP is removed or deprecated, bot replies and dashboard copy no longer frame
  progress as XP gain or level advancement.
- If XP is retained, the milestone documents the concrete product reason and
  adds a guardrail that XP stays secondary to weekly habit evidence.

## Verification

- `uv run pytest tests/test_dashboard.py tests/test_webhook.py` passes, or a
  narrower affected slice is documented with the reason.
- `uv run pytest tests/habits tests/gamification` passes or is updated to match
  the chosen XP removal path.
- `uv run ruff check .` is clean for Python changes.
- `npm run build` passes in `webapp/`.
- If schema cleanup is chosen, `uv run alembic upgrade head` succeeds from a
  fresh database and an existing development database.

## Sequencing notes

Do this before Milestone 14 corpus expansion. A larger lesson corpus will make
Kaizen better at giving grounded advice, but the dashboard first needs to show
the user a truthful, low-friction picture of consistency.

Avoid turning this into a general analytics milestone. The narrow product win is
that the user can open the Mini App, look under `LeetCode`, and immediately see
which days this week have evidence.

## Open questions

- Should `partial` evidence appear as its own marker style, or should it count
  as not done for the weekly visual while remaining inspectable in recent logs?
- Answered: XP is deprecated internally for this milestone. Existing
  `user_progress` and `habit_progress` tables stay until a separate cleanup
  migration after dashboard behavior is stable and `/me` compatibility is no
  longer needed.
- Should weekly rows show only active due days as empty circles, or should all
  non-done days look the same for faster scanning?

## Resume bullet unlocked

Reframed Kaizen's Mini App from XP gamification to a typed weekly habit evidence
dashboard, with per-habit weekday completion markers backed by effective habit
state and an explicit XP deprecation decision.
