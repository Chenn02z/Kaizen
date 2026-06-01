# Milestone 5 — Proactive agent

**Goal:** Assemble the LangGraph agent loop and add the scheduler so the agent
*decides* when a proactive nudge adds value — and can choose to stay silent.

**Unlocks:** the agentic credit; resume keywords agentic workflow, tool use,
LangGraph, scheduler/event-driven.

**Owner subagent:** `agent-engineer`

## Scope

In: a LangGraph graph with the three tools (`extract_facts`, `retrieve_techniques`,
`recall_history`) as nodes; message classification (log vs question vs check-in);
a scheduler that ticks on a cadence; the decide-or-stay-silent reasoning step;
a per-day intervention cap; the `interventions` table logging why each nudge was
sent and whether it was engaged with.

Out: evals + Langfuse harness (m6) — though leave the `interventions` table ready
for it.

## Prerequisites

Milestones 1–4 (all three tools exist and work standalone).

## Tasks

- [ ] `app/agent/`: LangGraph state machine wiring classify → tools → respond.
- [ ] Convert extraction, RAG retrieval, and memory recall into agent tools.
- [ ] Scheduler (APScheduler or a cron-hit endpoint) waking the agent N×/day,
      respecting quiet hours.
- [ ] Proactive node: pull recent facts + memory, reason about whether to
      intervene, choose technique + phrasing, or decide to stay silent.
- [ ] Daily cap enforced; `interventions` rows recorded with the reason.

## Acceptance criteria (verify each)

- On a "drifting" fixture (missed habit several days), a scheduler tick produces a
  grounded proactive message → test.
- On a "doing fine" fixture, the same tick decides to stay silent → test. (Both
  outcomes must be reachable — this is the agentic behavior.)
- The daily cap is never exceeded regardless of tick frequency → test.
- Each intervention writes an `interventions` row with its reason → query.

## Definition of done

Acceptance criteria tested (including the silence case), lint clean,
`code-reviewer` run, diff surgical.

## Resume bullet unlocked

Designed a LangGraph agent loop with tool use that autonomously decides when
intervention adds value, capped to avoid over-notifying.
