# Milestone 4 — Memory

**Goal:** The agent reasons over multi-week history without stuffing raw logs into
the context window, and can surface personal patterns.

**Unlocks:** the rarest keyword in this build; resume keyword agent memory,
longitudinal reasoning.

**Owner subagent:** `agent-engineer`

## Scope

In: Mem0 integration over the stored logs/facts plus the user's habit plan, a
`recall_history` capability, and pattern surfacing (e.g. "you relapse on
low-sleep days" or "you miss gym on weeks with late nights"). Reflection queries
("how was this week?", "when do I usually slip?") answered from memory + facts.

Out: proactive sending and the scheduler (m5), evals (m6).

## Prerequisites

Milestones 1–3.

## Tasks

- [ ] `app/memory/`: Mem0 setup; write extracted facts into memory as they land.
- [ ] `recall_history(query)` returning a compact, relevant slice of history.
- [ ] Reflection query handling: route "how was my week / when do I slip"
      questions through memory + `extracted_facts`.
- [ ] Simple pattern detection over recent facts (correlation between a
      trigger/condition and missed habits), ideally expressed against known
      habits from the habit plan rather than only raw free text.

## Acceptance criteria (verify each)

- After ingesting a multi-week fixture, `recall_history` returns relevant past
  events for a query without returning the entire log → test.
- "When do I usually slip?" yields an answer derived from the fixture's actual
  pattern → test against a planted pattern.
- Context sent to the model is bounded — memory summarizes rather than dumping all
  rows → assert on payload size.

## Definition of done

Acceptance criteria tested, lint clean, `code-reviewer` run, diff surgical.

## Resume bullet unlocked

Implemented a persistent memory layer (Mem0) enabling the agent to reason over
multi-week history and surface trigger/relapse patterns.
