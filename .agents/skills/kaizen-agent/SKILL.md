---
name: kaizen-agent
description: "Build Kaizen agent behavior: LangGraph graph, tools, Mem0 memory, scheduler, proactive intervention logic, quiet hours, and stay-silent decisions."
---

# Kaizen Agent

Use this skill for LangGraph, agent tools, memory, scheduler, and proactive
intervention work.

## Scope

- `app/agent/`
- `app/memory/`
- Scheduler endpoints or jobs
- Agent tests under `tests/agent/` and memory tests under `tests/memory/`

## Workflow

1. Read `AGENTS.md` and the memory/proactive milestone specs.
2. Inspect the graph, state, tools, scheduler, and memory payloads before
   editing.
3. Add tests for both intervention and stay-silent outcomes.
4. Implement bounded context assembly; summarize history instead of dumping raw
   rows.
5. Verify daily caps, quiet hours, intervention recording, and model gateway use.

## Rules

- A proactive agent must genuinely decide whether to intervene and may choose
  silence. A node that always sends is a defect.
- Enforce daily intervention caps and quiet hours.
- Record every intervention with its reason.
- Keep memory payloads bounded and tested.
- Model calls go through `app/llm/client.py`.
