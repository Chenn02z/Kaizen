# Milestone 2 — Structured extraction

**Goal:** Turn each freeform log into typed, queryable facts using an LLM with a
strict Pydantic schema.

**Unlocks:** the queryable behavioral history; resume keywords structured
outputs, LLM API integration, Pydantic.

**Owner subagent:** `backend-engineer` (extraction lives in `app/extract/`;
escalate model-prompt design questions in the delegation prompt).

## Scope

In: the `app/llm/client.py` gateway (retries, timeout, Langfuse-ready), an
extraction Pydantic schema, the extract call, an `extracted_facts` table linked
to `logs`, and wiring so every inbound log is extracted and stored.

Out: retrieval, memory, proactive behavior. The reply can stay a simple
acknowledgement for now.

## Prerequisites

Milestone 1 (logs flow in and persist).

## Tasks

- [ ] `app/llm/client.py`: single entry point for model calls; one provider;
      retries + timeout. No vendor SDK imported elsewhere.
- [ ] `app/extract/schema.py`: Pydantic v2 model — habit(s) referenced, adherence
      (yes/no/partial), mood, trigger, freeform context. Use enums where the set
      is closed.
- [ ] `app/extract/extractor.py`: prompt + call returning the schema; invalid
      JSON → validation error path, never regex parsing.
- [ ] `extracted_facts` table + migration; one row per log.
- [ ] Hook extraction into the webhook flow.

## Acceptance criteria (verify each)

- A test log produces a valid `ExtractedFacts` object with expected fields → test
  against 5–10 hand-written examples.
- Each inbound message creates one linked `extracted_facts` row → query.
- A malformed model response is caught as a validation error, not a crash → test
  with a stubbed bad response.
- All model traffic goes through `app/llm/client.py` → grep shows no other SDK
  import.

## Definition of done

Acceptance criteria tested, lint clean, `code-reviewer` run, diff surgical. Keep
the hand-written examples — they seed the milestone-6 eval set.

## Resume bullet unlocked

Implemented structured-output extraction (Pydantic v2) converting unstructured
logs into typed behavioral facts, with schema validation on every model call.
