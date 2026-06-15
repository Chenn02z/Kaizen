---
name: kaizen-evals
description: "Build and run Kaizen evaluation and observability workflows: golden sets, LLM-as-judge rubrics, reproducible reports, and Langfuse tracing."
---

# Kaizen Evals

Use this skill for eval harnesses, judge prompts, metrics reports, and Langfuse
observability.

## Scope

- `evals/`
- `tests/evals/`
- Langfuse tracing in `app/llm/client.py`
- Reports such as `evals/RESULTS.md`

## Workflow

1. Read `AGENTS.md` and the eval/observability milestone spec.
2. Inspect existing golden examples, judge rubrics, runner code, and tests.
3. Keep the runner reproducible and re-runnable so deltas are measurable.
4. Score against an explicit rubric: specific, grounded in a real technique,
   right tone, and actionable.
5. Run the eval or focused tests and report only measured results.

## Rules

- Reuse hand-written examples from extraction and RAG milestones as seeds.
- Record both comparison numbers when evaluating variants such as reranking on
  versus off.
- Do not hand-edit or fabricate metrics.
- If a metric is not measured yet, say so and add the measurement when it is in
  scope.
- Langfuse should trace latency, token cost, and tool calls for model calls.
