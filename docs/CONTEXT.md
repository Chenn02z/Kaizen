# Kaizen Context

Canonical terminology for product discussions and milestone planning.

## Terms

- `category`: an organizational grouping for related `habit`s used in
  onboarding, review, and presentation. A category is not itself due, inferred,
  missed, or nudged.
- `log`: a user's freeform Telegram message about their day, behavior, or
  reflection.
- `multi-habit log`: a single `log` that provides evidence for more than one
  `habit`. In v1, one log may satisfy multiple habits if the message clearly
  mentions each one.
- `habit`: a tracked behavior the user wants to build or break.
- `habit alias`: an example phrase, synonym, or natural-language expression that
  helps Kaizen map a `log` onto a known `habit`. Habit aliases are soft anchors
  for extraction, not separate habits.
- `progress evidence`: a phrase in a `log` that indicates the user made
  meaningful progress on a `habit`, even if the exact wording differs across
  days. For example, "started a new personal project", "worked on a feature",
  and "shipped a fix" can all count as evidence for the same project habit.
- `precision bias`: when habit matching is ambiguous, Kaizen should prefer
  leaving a `log` unmatched rather than over-crediting a `habit`. In v1, trust
  is more important than maximizing automatic matches.
- `habit plan`: the explicit definition of a `habit`, including its intended
  cadence, success condition, known triggers, goals, and optional habit aliases.
  Kaizen uses the habit plan as the source of truth when deciding whether the
  user is drifting or has missed an expected behavior.
- `cadence`: the expected frequency for a `habit`, such as daily, specific
  weekdays, or N times per week. Cadence determines when a habit is due and
  when a missed-day fallback `check-in` is justified.
- `v1 cadence patterns`: the only cadence types supported in v1 are `daily`,
  `specific weekdays`, and `N times per week`.
- `check-in`: an explicit yes/no/partial confirmation requested only when the
  day's habit completion is ambiguous or missing from the user's natural-language
  `log`s. Kaizen should infer adherence from `log`s by default.
- `fallback check-in`: a same-day `check-in` Kaizen may send automatically when
  a due `habit` has no relevant `log` by its expected window. It should be sent
  at most once per day and only for habits that were actually due.
- `technique`: a grounded behavioral-science method retrieved from the corpus.
- `nudge`: a proactive message sent by the agent.
- `intervention`: a `nudge` that is intentionally delivered, recorded, and
  reviewed.
- `quiet hours`: times when proactive messages must stay silent.
- `grounded`: advice tied to a real `technique` and the user's own history.
- `dashboard`: the Telegram Mini App surface for read-only review of habit
  state, recent logs, progress, and recorded interventions. In v1, the
  dashboard does not create or edit habit plans; Telegram chat remains the
  logging and check-in surface.
