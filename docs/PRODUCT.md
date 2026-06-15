# Kaizen — Product Requirements (PM view)

Owner: you (solo) · Status: in progress · Last updated: 2026-06-15

This document is the *why* and *what*. The *how* lives in `milestones/` and
`../CLAUDE.md`. When a build decision is ambiguous, this file is the tiebreaker.

---

## 1. Problem

I tried existing habit products and they helped me record intentions, but they
did not reliably change my behavior. They still depended on me to open the app,
interpret my own patterns, and recover after I drifted.

Changing habits fails for boring, well-understood reasons: people do not notice
their own patterns, they get generic advice that does not fit their situation,
and nothing reaches them *at the moment that matters*. Existing habit trackers
are often passive logbooks. Coaching apps may feel supportive, but they often
stay generic. Neither gives me personal, timely accountability in the place I
already show up every day.

## 2. Vision

Kaizen is the system I wanted instead: a Telegram-native companion that behaves
like an attentive coach. I can text it the way I already talk to a friend. It
knows my history, notices when I am drifting, and reaches out with the right
specific thing at the right time — grounded in behavioral science, not
motivational filler.

## 3. Users & context

- **Primary user:** the builder (single user, v1). Real daily usage is a hard
  requirement, not a nice-to-have — it's the only source of honest metrics.
- **Why Telegram:** the product should live in a channel I already use daily, so
  logging and nudges happen with minimal friction instead of requiring me to
  remember to open a separate app.
- **Secondary audience:** a hiring engineer reading the repo. The product must
  demonstrate production-grade AI engineering (RAG, memory, agentic decisions,
  evals, observability), not a thin LLM wrapper.

The litmus test for every feature: **if you removed the LLM, would it still
work?** If yes, the AI is decorative — redesign it.

## 4. Goals

- G1 — Make logging effortless: capture a day's behavior in one natural-language
  Telegram message.
- G2 — Turn unstructured logs into a queryable behavioral history.
- G3 — Give advice that is *specific* (grounded in a named technique) and
  *personal* (informed by the user's own history).
- G4 — Provide context-aware accountability: intervene proactively and
  judiciously when I am drifting, and stay silent otherwise.
- G5 — Prove the AI is actually good via measurable evals, not vibes.

## 5. Non-goals (v1)

- Multi-user, accounts, social features.
- A rich graphical dashboard (Telegram-only; charts are a later Mini App).
- Mobile/native app, App Store presence.
- Medical or clinical claims. This is a self-improvement tool, not therapy.
- Wearable/health-data integrations (later, via MCP).

## 6. Core user stories

- As the user, I text a freeform log ("rough day, skipped gym, doomscrolled till
  2am") and it's captured and understood without forms.
- As the user, I do not need to remember to open a separate habit app just to
  keep the system useful.
- As the user, I should not need explicit checklists most days; my natural-language
  logs should be enough unless the day is ambiguous.
- As the user, I ask "how did this week go?" or "when do I usually slip?" and get
  an answer grounded in my actual logs.
- As the user, I receive an unprompted, well-timed nudge on a known weak point —
  but I'm never spammed.
- As the user, the advice references a real technique (e.g. implementation
  intentions) rather than generic encouragement.
- As the maintainer, I can see whether a change made interventions better or
  worse via an eval score and Langfuse traces.

## 7. Functional requirements

- FR1 Onboarding: define categories and habits to build/break, with each habit
  stored as an explicit habit plan containing cadence, success condition, known
  triggers, goals, and optional aliases/examples for natural-language matching.
- FR1a Habit success conditions should be concrete enough to judge from a `log`,
  but broad enough to capture real progress. Example: "made meaningful progress
  on a personal project" is better than requiring only "shipped a feature".
- FR1b Each habit must have explicit cadence, such as daily, specific weekdays,
  or N times per week, so Kaizen can determine when the habit was due.
- FR1c V1 cadence support is intentionally limited to three patterns: daily,
  specific weekdays, and N times per week.
- FR2 Natural-language logging via Telegram (text, v1).
- FR2a Adherence inference: infer habit completion from natural-language logs by
  default; request an explicit check-in only when the day is ambiguous or
  missing.
- FR2b Fallback check-in: if a due habit has no relevant log by its expected
  window, Kaizen may send one same-day fallback check-in instead of waiting
  until the next morning.
- FR3 Structured extraction: each log → typed facts (habit, adherence, mood,
  trigger, context).
- FR3a A single log may satisfy multiple habits when it contains clear evidence
  for each one.
- FR3b When matching is ambiguous, Kaizen should prefer precision over recall:
  leave the habit unmatched and rely on a later fallback check-in rather than
  incorrectly marking the habit complete.
- FR4 Persistent memory: longitudinal profile the agent reasons over.
- FR5 Grounded coaching via RAG over a curated behavioral-science corpus.
- FR6 Pattern detection (e.g. trigger/relapse correlations).
- FR7 Proactive interventions: scheduled + agent-decided, with a daily cap.
- FR8 Reflection queries + an automatic weekly review.

## 8. Success metrics

**Product (does it help me?)**
- Days of real usage (target: 60+ continuous).
- Logging consistency (% of days logged).
- Self-reported adherence trend over the usage window.

**Technical (is the AI good?)**
- Grounded-response rate (LLM-as-judge): advice tied to a real technique.
- Extraction field accuracy vs a hand-labeled set.
- Proactive precision: % of nudges the user engages with (not ignored).
- p95 reply latency and token cost per interaction (Langfuse).

**Meta (does it earn the resume bullet?)**
- Each milestone ships a measurable delta backed by the eval harness and a public
  repo with tests.

## 9. Scope & roadmap

The current repo milestone files are `01` through `07` under `docs/milestones/`.
The core accountability path is milestones 1, 2, 3, 5, 6, and 7, with
gamification as an additional retention layer:

1. Skeleton — Telegram ⇄ FastAPI ⇄ Postgres.
2. Extraction — logs → typed facts.
3. RAG — grounded coaching.
4. Gamification — XP, progression, and Mini App stats.
5. Memory — longitudinal reasoning.
6. Proactive agent — agent-decided interventions.
7. Evals + observability — proof it works.

Post-v1 (explicitly later, becomes "future work" + v2 keywords): Telegram Mini
App dashboard, MCP calendar/health integration, voice logging, multi-agent
analysis, multi-user.

## 10. Risks & mitigations

- **Gimmick risk** (AI not load-bearing) → enforce the litmus test in §3; the
  agent must *decide*, not just template messages.
- **Over-notification** → hard daily cap + the agent can choose silence (m5).
- **Generic advice** → RAG grounding requirement (m5/FR5); evals gate it (m6).
- **Invented metrics** → metrics come from real usage + the harness only. Never
  fabricate numbers for the resume.
- **Privacy** → personal data stays in your own DB; no third-party calls beyond
  the model/embeddings/Langfuse.
- **Scope creep** → anything in §5 or §9-post-v1 is out until v1 ships.

## 11. Open questions

- Initial v1 habit plan seed:
  - `FITNESS` → `run`: N times per week
  - `FITNESS` → `gym`: N times per week
  - `CAREER` → `leetcode`: daily
  - `CAREER` → `personal project`: N times per week
  - `SELF` → `read`: daily
- Cadence and quiet hours for proactive checks? (Decide before m5.)
- Cost ceiling per month? (Drives model + caching choices.)
