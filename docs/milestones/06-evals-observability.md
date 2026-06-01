# Milestone 6 — Evals & observability

**Goal:** Prove the AI is good with measurable evals, and trace every model call.
This is the milestone that turns the project from a hobby into a case study.

**Unlocks:** the differentiator; resume keywords LLM evals, LLM-as-judge,
observability, Langfuse.

**Owner subagent:** `eval-engineer`

## Scope

In: a golden eval set, an LLM-as-judge harness with a rubric, an
intervention/adherence correlation report, and Langfuse tracing wired through the
LLM gateway. Produce honest before/after numbers.

Out: new product features. This milestone measures what exists.

## Prerequisites

Milestones 1–5 (a full pipeline to evaluate). Reuse the hand-written examples
saved in m2/m3.

## Tasks

- [ ] `evals/`: golden set of ~20–30 scenarios (log → ideal response notes).
- [ ] LLM-as-judge scoring each generated reply on a rubric: specific?
      grounded in a real technique? right tone? actionable?
- [ ] A runner that scores the current system and prints aggregate metrics;
      re-runnable so you can measure deltas (e.g. with vs without reranking).
- [ ] Correlation report: interventions vs subsequent logged adherence over real
      usage.
- [ ] Langfuse wired in `app/llm/client.py`: traces, token cost, latency, tool
      calls on every model interaction.

## Acceptance criteria (verify each)

- The harness runs end-to-end and outputs per-criterion + aggregate scores → run
  it.
- Toggling a real lever (e.g. reranking off) changes the grounded-response score
  measurably → record both numbers; this is your before/after.
- Langfuse shows a trace per interaction with latency + token cost → verify in
  the dashboard.
- Reported metrics come only from the harness and real usage — no hand-edited
  numbers.

## Definition of done

Harness reproducible, numbers recorded in the repo (e.g. `evals/RESULTS.md`),
lint clean, `code-reviewer` run, diff surgical.

## Resume bullet unlocked

Built an LLM-as-judge eval harness measuring intervention quality (raising
grounded-response rate from X% to Y%) and instrumented the system with Langfuse
for latency, cost, and tool-call tracing.
