# Kaizen — Product Requirements (PM view)

Owner: you (solo) · Status: pre-build · Last updated: at kickoff

This document is the *why* and *what*. The *how* lives in `milestones/` and
`../CLAUDE.md`. When a build decision is ambiguous, this file is the tiebreaker.

---

## 1. Problem

Changing habits fails for boring, well-understood reasons: people don't notice
their own patterns, they get generic advice that doesn't fit their situation,
and nothing reaches them *at the moment that matters*. Existing habit trackers
are passive logbooks — they record what you did but never reason about it or
reach out first.

## 2. Vision

A companion that behaves like an attentive coach: it knows your history, it
notices when you're drifting, and it says the right specific thing at the right
time — grounded in real behavioral science, not motivational filler. You talk to
it the way you'd text a friend; it does the thinking.

## 3. Users & context

- **Primary user:** the builder (single user, v1). Real daily usage is a hard
  requirement, not a nice-to-have — it's the only source of honest metrics.
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
- G4 — Intervene proactively and judiciously — reach out when it helps, stay
  silent otherwise.
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
- As the user, I ask "how did this week go?" or "when do I usually slip?" and get
  an answer grounded in my actual logs.
- As the user, I receive an unprompted, well-timed nudge on a known weak point —
  but I'm never spammed.
- As the user, the advice references a real technique (e.g. implementation
  intentions) rather than generic encouragement.
- As the maintainer, I can see whether a change made interventions better or
  worse via an eval score and Langfuse traces.

## 7. Functional requirements

- FR1 Onboarding: define habits to build/break, known triggers, goals.
- FR2 Natural-language logging via Telegram (text, v1).
- FR3 Structured extraction: each log → typed facts (habit, adherence, mood,
  trigger, context).
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

v1 is milestones 1–6 (see `milestones/`). Each is independently shippable and
unlocks a concrete capability:

1. Skeleton — Telegram ⇄ FastAPI ⇄ Postgres.
2. Extraction — logs → typed facts.
3. RAG — grounded coaching.
4. Memory — longitudinal reasoning.
5. Proactive agent — agent-decided interventions.
6. Evals + observability — proof it works.

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

- Which specific habits/triggers to seed at onboarding? (Personal — fill before
  m1.)
- Cadence and quiet hours for proactive checks? (Decide before m5.)
- Cost ceiling per month? (Drives model + caching choices.)
