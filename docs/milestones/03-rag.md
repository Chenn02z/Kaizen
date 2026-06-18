# Milestone 3 — RAG grounding

**Goal:** Replies are grounded in real behavioral-science techniques retrieved
from a curated corpus of self-authored lessons, not generic LLM advice.

**Unlocks:** the core AI-engineering signal; resume keywords RAG, vector
database, embeddings, semantic search, reranking.

**Owner subagent:** `rag-engineer`

## Scope

In: a corpus of ~100–200 self-authored lesson chunks, an embedding pipeline,
pgvector storage + similarity search, a reranking step, and a coaching reply
that cites the retrieved technique.

Out: memory/longitudinal reasoning (m5), proactive sending (m6).

## Prerequisites

Milestones 1–2 (logs + extracted facts available to use as the retrieval query).

## Tasks

- [ ] `corpus/`: markdown lesson chunks in your own words. Each chunk should map
      a source idea to a technique such as implementation intentions, habit
      stacking, temptation bundling, urge surfing, two-minute rule, relapse
      recovery, environment design, or friction reduction.
- [ ] Each lesson chunk includes enough structure for retrieval and application:
      source, technique, lesson, use when, avoid when, and example application.
- [ ] `corpus_chunks` table with a pgvector embedding column + migration.
- [ ] `app/rag/embed.py`: embed + upsert corpus; cache to avoid re-embedding.
- [ ] `app/rag/retrieve.py`: top-k cosine search, then a rerank pass over the
      candidates.
- [ ] Reply path: build the query from the latest log/facts, retrieve, and
      generate a grounded response that names the technique used.

## Acceptance criteria (verify each)

- A "skipped gym, no motivation" log retrieves relevant lesson chunks (e.g.
  implementation intentions) in the top results → test on fixed queries.
- Corpus chunks are self-authored summaries rather than copied passages from
  source books or articles → inspect the corpus.
- Reranking changes ordering measurably vs raw similarity on at least one query →
  test/assert.
- The generated reply references the retrieved technique, not generic advice →
  spot check + a judge check reused in m7.
- Embeddings are cached: a second run does not re-embed unchanged chunks → test.

## Definition of done

Acceptance criteria tested, lint clean, `code-reviewer` run, diff surgical.

## Resume bullet unlocked

Engineered a RAG pipeline (embeddings + pgvector + reranking) grounding coaching
in a ~150-entry corpus of self-authored behavioral-science lesson notes.
