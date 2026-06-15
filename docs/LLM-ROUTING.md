# Kaizen LLM Routing Policy

This is the intended model-routing policy for Kaizen once the OpenAI models are
introduced into the gateway.

## Default shape

- `gpt-5.5` is the orchestrator and final synthesizer.
- `gpt-5.4 mini` is the specialist model for narrow, bounded tasks.

## Use `gpt-5.5` for

- top-level routing and branch selection
- ambiguity resolution
- final user-facing synthesis
- proactive intervention decisions
- any case where the reply must weigh multiple tool outputs or tradeoffs

## Use `gpt-5.4 mini` for

- structured extraction
- classification
- retrieval reranking
- bounded memory summarization
- short draft replies
- simple transforms that have a clear schema and little branch logic

## Routing rules

- Prefer the smaller model by default for bounded tasks.
- Escalate to the orchestrator only when the result affects user-facing
  behavior, when the task is ambiguous, or when multiple specialist outputs must
  be reconciled.
- Keep specialist prompts short and stable so they are cache-friendly.
- Keep orchestrator prompts compact by passing summaries, not raw transcripts.
- Do not use the orchestrator for every sub-step.
- Do not duplicate long shared context across multiple calls if one shared state
  object is enough.

## Cost control

- If a task is deterministic and schema-bound, start with `gpt-5.4 mini`.
- If the orchestrator only needs to choose a branch, keep the branch prompt
  short and let specialists do the detailed work.
- If a task becomes repetitive, consider prompt caching or a reusable system
  prefix before increasing model size.

## Current repo note

The current codebase still routes through a single model gateway in
`app/llm/client.py`. This policy is the target structure, not a claim about the
present implementation.
