# Kaizen Learning Roadmap

## How to use this roadmap
Choose lessons that sit one step ahead of the current milestone or coding task. Each lesson should help me ship Kaizen, understand the underlying AI engineering concept, and create evidence I can later explain in an interview.

## Current focus
- Learn through the next active milestone and the code paths it touches.

## Learning tracks

### Foundations and delivery
- Why it matters: I need a reliable base before the AI layers matter.
- Repo anchors: `docs/milestones/01-skeleton.md`, `AGENTS.md`, `app/`, `tests/`
- Likely lessons:
  - FastAPI webhook flow through the app
  - Async boundaries and why they matter here
  - What "definition of done" means in this repo
- Proof signals:
  - Passing tests for the touched milestone
  - Clean linting
  - Clear explanation of request flow and system boundaries

### Structured extraction
- Why it matters: extraction turns freeform logs into queryable state.
- Repo anchors: `docs/milestones/02-extraction.md`, `app/llm/client.py`, extraction-related tests
- Likely lessons:
  - Pydantic-validated structured outputs
  - Prompt design for extraction without regex parsing
  - Failure modes in typed extraction
- Proof signals:
  - Extraction tests
  - Schema definitions I can explain
  - Concrete examples of extraction errors and fixes

### Retrieval and grounding
- Why it matters: Kaizen should give advice tied to real behavioral techniques, not generic filler.
- Repo anchors: `docs/milestones/03-rag.md`, `app/rag/`, `tests/`, `evals/`
- Likely lessons:
  - Embeddings, chunking, and retrieval flow
  - What "grounded" means in this project
  - How to reason about recall, precision, and reranking
- Proof signals:
  - Retrieval tests and evals
  - Clear explanation of the corpus-to-answer path
  - Ability to justify a retrieval design choice

### Memory and agent reasoning
- Why it matters: the product becomes materially better when it reasons over history and decides when silence is better.
- Repo anchors: `docs/milestones/05-memory.md`, `docs/milestones/06-proactive-agent.md`, `app/`, `evals/`
- Likely lessons:
  - What should become memory versus immediate context
  - LangGraph state and decision boundaries
  - Intervention caps, quiet hours, and stay-silent logic
- Proof signals:
  - Passing milestone tests
  - Ability to explain an intervention decision
  - Traceable reasoning artifacts in code or Langfuse

### Evals and observability
- Why it matters: this is what turns the repo from a demo into evidence.
- Repo anchors: `docs/milestones/07-evals-observability.md`, `evals/`, `tests/evals/`
- Likely lessons:
  - Golden sets and judge rubrics
  - Groundedness versus vibes
  - Cost, latency, and trace-based debugging
- Proof signals:
  - Reproducible eval outputs
  - Langfuse traces I can discuss
  - Measurable before/after improvement claims
