# Kaizen Product Requirements

Owner: solo builder | Status: in progress | Last updated: 2026-10-25

This is the product contract for Kaizen. The concrete habit list, inputs, and
build order live in `docs/DIRECTION.md`.

## Product Summary

Kaizen is a Telegram-native behavior-change companion for one user. The user
logs daily life in natural language; Kaizen extracts structured habit evidence,
remembers patterns, retrieves grounded behavioral-science techniques from the
builder's own lesson notes, and intervenes only when a timely nudge is likely to
help.

The product solves a specific failure mode in habit apps: passive tracking still
requires the user to open an app, interpret patterns, and recover alone after
drift. Kaizen should feel like a quiet coach inside the chat the user already
opens every day.

## Target User

The primary user is the builder using Kaizen for real habit change. The
secondary audience is a hiring engineer evaluating the repo as an AI engineering
case study. The product must be useful in daily life and technically credible:
structured extraction, RAG, memory, agentic decisions, evals, and observability
must all be load-bearing.

## User Experience Requirements

- Kaizen tracks a fixed habit list (gym, run, weigh-in, sleep, LeetCode,
  system design, doomscrolling). Inputs are one-tap iPhone Shortcut buttons,
  short Telegram sentences, on-device Shortcuts automations, and the Google
  Health API. Every log gets a one-line confirmation with weekly progress.
- LeetCode sentences are parsed into problem, pattern, difficulty, and
  struggle; Kaizen saves immediately, asks at most one optional follow-up, and
  schedules re-solves at +3, +10, and +30 days.
- Kaizen sends one morning brief per day: sleep vs target, social-app opens,
  today's gym split, one LeetCode pick, and weekly progress.
- The user can send a freeform Telegram `log` such as "rough day, skipped gym,
  doomscrolled until 2am" without filling out forms.
- Kaizen stores each `log`, extracts typed facts, and maps clear evidence to
  known `habit`s from the user's habit plan.
- Habits have cadence, success condition, aliases, known triggers, goals, and
  expected evidence windows.
- A single `log` may satisfy multiple habits when the evidence is clear. When a
  match is ambiguous, Kaizen must prefer leaving the habit unmatched over
  falsely granting credit.
- Kaizen can answer `reflection question`s such as "how did this week go?" or
  "when do I usually slip?" using the user's actual history.
- When a `reflection question` asks what to change or try next, Kaizen should
  combine the user's history with retrieved `lesson`s from the corpus.
- Advice must be `grounded`: tied to a named behavioral-science `technique`, a
  relevant self-authored `lesson` when useful, and the user's own recent context,
  not generic encouragement.
- Kaizen may send a fallback `check-in` when a due habit has no evidence by its
  expected window.
- Kaizen may send a proactive `nudge` only when the agent sees a useful moment
  to intervene. It must respect `quiet hours`, enforce a daily cap, and stay
  silent when appropriate. Proactive ticks may use retrieved `lesson`s to choose
  the intervention strategy, but they must not become generic lesson broadcasts.
- A Google Sheet, rewritten nightly by the backend, is the read-only
  dashboard with `Weekly` and `Daily` tabs. It replaces the Telegram Mini App.
- Progress feedback is secondary to the core accountability loop: log,
  understand, reflect, intervene. Weekly habit evidence is the primary progress
  surface; XP and levels may remain as internal compatibility infrastructure
  but should not drive the dashboard hierarchy.

## Technical Requirements

- Backend: Python 3.12, FastAPI, async SQLAlchemy, Alembic, PostgreSQL, and
  pgvector.
- Telegram webhook: verify the webhook secret, allow only `ALLOWED_USER_ID`,
  persist logs, handle `/start`, `/dashboard`, and `/app` without storing those
  commands as logs.
- LLM gateway: all completion and embedding calls go through `app/llm/client.py`;
  no other module imports vendor SDKs directly.
- Structured extraction: model output for extraction or decisions is validated
  with Pydantic v2. Do not parse model free text with regex.
- Habit state: cadence support is limited to daily, specific weekdays, and N
  times per week for v1.
- RAG: retrieve and rerank curated corpus chunks from pgvector. Corpus entries
  are self-authored `lesson`s distilled from books, articles, or experience,
  mapped to behavioral-science `technique`s; generated coaching must name the
  technique it uses and avoid copying source text.
- Memory: write extracted facts to memory and recall compact history for
  reflection and agent decisions without dumping all logs into context.
  Action-oriented reflection answers may retrieve `lesson`s after recalling the
  user's relevant history.
- Agent loop: LangGraph routes user messages through extraction, retrieval,
  memory, and response generation; scheduled ticks handle due-habit checks,
  fallback check-ins, proactive decisions, or silence.
- Scheduler: run app-local ticks outside quiet hours, record all check-ins,
  nudges, and silence decisions in `interventions`.
- Dashboard: backend read models, not React-only inference, derive habit status
  from persisted logs, extracted facts, habit plans, evidence overrides, and
  interventions.
- Integrations: Google Health API for sleep, Google Sheets API for the
  dashboard, and Shortcuts posts to the webhook for buttons, weight, and
  social-app opens.
- Observability: Langfuse traces model calls with latency, token usage, and
  cost.

## Success Metrics

- Product: 60+ continuous days of real use, logging consistency, and improving
  self-reported adherence over time.
- Extraction: field accuracy against a hand-labeled log set, including
  multi-habit and ambiguous-log cases.
- Grounding: judge-scored rate of replies and reflection answers that cite and
  correctly apply a real technique and relevant lesson.
- Proactivity: share of nudges that receive useful engagement, with spam
  prevented by quiet hours and the daily cap.
- System: p95 reply latency, token cost per interaction, passing tests, and
  clean traces.

## Scope Boundaries

V1 is single-user, Telegram-first, and read-only for dashboard habit review. It
does not include multi-user accounts, social features, clinical claims, native
mobile apps, or habit editing inside the dashboard. Wearable data is limited
to sleep via the Google Health API.

The product bar is simple: if the LLM were removed and the feature would still
work just as well, the AI is decorative. Redesign the feature until the model is
responsible for a real judgment: understanding logs, grounding advice, recalling
patterns, or deciding whether to intervene.
