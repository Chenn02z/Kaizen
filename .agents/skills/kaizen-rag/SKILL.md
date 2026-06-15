---
name: kaizen-rag
description: "Build and improve Kaizen RAG: behavioral corpus chunks, embeddings, pgvector storage, retrieval, reranking, and grounded replies."
---

# Kaizen RAG

Use this skill for retrieval-quality work, corpus changes, embeddings, pgvector,
reranking, and grounded behavioral-science replies.

## Scope

- `corpus/`
- `app/rag/`
- RAG-related tests under `tests/rag/` and `tests/evals/`
- Grounded reply generation that cites retrieved techniques

## Workflow

1. Read `AGENTS.md` and the relevant RAG/eval milestone spec.
2. Inspect corpus format, embedding cache behavior, retrieval code, and tests.
3. Add or update fixed-query tests before changing retrieval behavior.
4. Preserve the two-stage pipeline: similarity search, then rerank.
5. Verify relevance and whether reranking changes ordering when expected.

## Rules

- Model and embedding calls go through `app/llm/client.py`.
- Cache embeddings; do not re-embed unchanged corpus chunks.
- Corpus chunks must be self-contained, plain prose, and not copied verbatim
  from sources.
- Grounded replies must name the technique they use. Generic advice is a defect.
- If retrieval quality cannot be measured yet, add a focused eval or state the
  missing measurement plainly.
