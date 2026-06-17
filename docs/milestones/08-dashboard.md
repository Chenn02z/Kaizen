# Milestone 8 — Read-only Telegram dashboard

**Goal:** Promote the Telegram Mini App from a stats sheet into Kaizen's main
read-only review surface: today's habit state, recent logs, progress, and
recorded interventions, launched inside Telegram without the external-site flow.

**Unlocks:** the product surface users actually return to; resume keywords
Telegram Mini App, dashboard, read models, habit analytics, productized AI UX.

**Owner subagent:** `frontend-engineer` with backend support for dashboard JSON
read models and Telegram launch glue.

## Scope

In: Mini App launch as a real Telegram `web_app`, a dashboard JSON endpoint,
read-only dashboard UI, and tests proving the dashboard reflects persisted
habit/log/intervention state.

Out: habit creation or editing, arbitrary charts, multi-user access, native
mobile app, and new third-party analytics.

## Prerequisites

Milestones 1, 2, 4, and 6. The dashboard reads from existing `logs`,
`extracted_facts`, `habit_plans`, `user_progress`, `habit_progress`, and
`interventions`; it should not introduce a parallel frontend-only source of
truth.

## Product decisions

- The `dashboard` is the main in-Telegram review surface.
- Telegram chat remains the surface for `log`s, fallback `check-in`s, and
  proactive `nudge`s.
- V1 dashboard is read-only. It can reveal habit-plan state, but it must not
  create, edit, reorder, or delete habit plans.
- XP remains visible, but it is not the dashboard's primary information
  architecture. The first screen should answer: what is due, what is done, what
  is missing, and what happened recently?

## Dashboard read model

Add a backend read model for the Mini App. It can extend `/me` or introduce a
new endpoint such as `GET /dashboard`; choose the smallest implementation that
keeps the existing `/me` contract stable for current tests.

The response should include:

- Overall progress: level, XP, XP to next level.
- Habit progress: habit name, category, level, XP, cadence, and today's status
  (`done`, `missing`, `not_due`, or `unknown`).
- Recent logs: newest-first text, timestamp, extracted habits, adherence, mood,
  trigger, and context.
- Recent interventions: newest-first kind, timestamp, reason, technique,
  message, and engagement state.

Derived fields should come from persisted rows and existing habit-plan logic.
Do not infer dashboard-only state in React.

## Tasks

- [ ] Telegram launch: rename the menu button to `Dashboard`, centralize the
      Mini App URL, and add `/start`, `/dashboard`, and `/app` command handling
      that sends an inline `web_app` button instead of a plain URL.
- [ ] Backend API: add Pydantic response models and a dashboard read function
      that joins habit plans, progress, recent logs/facts, and recent
      interventions for the configured single user.
- [ ] Frontend API client: fetch the dashboard read model from the Mini App and
      keep `/me` compatibility unless `/me` is intentionally replaced.
- [ ] Mini App UI: redesign the first screen around review sections:
      `Today`, `Habits`, `Recent logs`, and `Interventions`. Use Telegram theme
      variables and `@telegram-apps/telegram-ui`.
- [ ] Empty/error states: show useful read-only states when there are no logs,
      no progress rows, no recent interventions, or the backend returns 403/503.
- [ ] Docs: update `README.md` or Mini App docs with the required BotFather
      setup: public HTTPS `PUBLIC_URL`, Mini App domain, webhook, and menu
      button behavior.

## Acceptance criteria (verify each)

- Sending `/start`, `/dashboard`, or `/app` from the allowed Telegram user sends
  a message with a Telegram `web_app` inline button pointing at
  `{PUBLIC_URL}/miniapp`; the command is not inserted as a `log`.
- The Mini App menu button is registered as `Dashboard` and uses the same
  Mini App URL helper as the command button.
- The dashboard endpoint returns valid typed JSON for a fixture containing habit
  plans, progress rows, extracted facts, logs, and interventions.
- Today's habit status is derived from cadence and extracted facts, including at
  least one `done` habit and one `missing` habit in tests.
- The Mini App renders the review sections from backend data without hardcoded
  fixture values.
- `npm run build` succeeds in `webapp/`.

## Definition of done

Acceptance criteria tested, `uv run pytest` passes for dashboard/webhook tests,
`uv run ruff check .` is clean for Python changes, `npm run build` passes in
`webapp/`, and the production Telegram bot opens the Mini App without the
external-site warning when launched from the bot menu or command button.

## Resume bullet unlocked

Built a Telegram-native read-only habit dashboard backed by typed FastAPI read
models, showing daily habit state, recent logs, and recorded interventions from
the agent pipeline.
