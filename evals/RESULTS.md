# Eval results

All numbers are produced by the harness in `evals/` — never hand-edited. Re-run
the commands below to reproduce.

## Setup

- Date: 2026-06-04
- Golden set: 25 scenarios (`evals/golden.py`), each a daily log mapped to 1–2
  expected corpus techniques (filename stems).
- Corpus: 15 behavioral-science techniques (`corpus/`), embedded with
  `text-embedding-3-small`.
- Rerank model: `claude-haiku-4-5` via `app/llm/client.py`.
- Metric definitions: `evals/retrieval.py`.
  - **hit-rate** — fraction of scenarios where ≥1 expected technique appears in top_n.
  - **recall@k** — fraction of expected techniques found in top_n, averaged over scenarios.
  - **MRR** — mean reciprocal rank of the first expected-technique hit in top_n.

## Eval B — Retrieval, rerank ON vs OFF (the lever)

Reproduce:

```bash
uv run python -m evals.retrieval            # rerank ON
uv run python -m evals.retrieval --no-rerank  # rerank OFF
```

At production defaults (`top_k=5, top_n=3`):

| metric    | rerank OFF | rerank ON | delta   |
|-----------|------------|-----------|---------|
| hit-rate  | 0.76       | **0.96**  | +0.20   |
| recall@k  | 0.64       | **0.74**  | +0.10   |
| MRR       | 0.64       | **0.81**  | +0.17   |

The gap widens as `top_k` grows (more candidates for the reranker to reorder);
rerank-OFF is flat because it just takes the top-3 by cosine distance:

| top_k | OFF hit-rate | ON hit-rate | ON recall@k | ON MRR |
|-------|--------------|-------------|-------------|--------|
| 5     | 0.76         | 0.96        | 0.74        | 0.81   |
| 8     | 0.76         | **1.00**    | 0.82        | 0.88   |
| 12    | 0.76         | 1.00        | 0.80        | 0.83   |

## Bug surfaced by the eval

Before the eval existed, reranking was **silently a no-op in production**:
`_rerank` parsed the model output with `json.loads()` directly, but the model
wraps its JSON array in a markdown fence (```` ```json … ``` ````), so parsing
threw and the `except` branch returned the raw cosine order — identical to
rerank-OFF. The eval caught this (ON == OFF at every `top_k`). Fixed in
`app/rag/retrieve.py` by extracting the JSON array before parsing. The table
above is the post-fix result; pre-fix, every "ON" cell equalled its "OFF" cell.

## Eval A — Reply quality (LLM-as-judge)

Reproduce (real API calls — gated as a script, not run under pytest):

```bash
uv run python -m evals.runner            # rerank ON
uv run python -m evals.runner --no-rerank  # rerank OFF
```

Each scenario's log is retrieved -> `compose_log_reply` -> scored by the judge
(`evals/judge.py`) on four boolean criteria. n=25, single run, `claude-haiku-4-5`.

| criterion   | rerank OFF | rerank ON |
|-------------|------------|-----------|
| specific    | 100%       | 100%      |
| right_tone  | 100%       | 100%      |
| actionable  | 92%        | 96%       |
| **grounded** (headline) | **72%** | 64% |

### Reading these honestly

The grounded-response rate is *lower* with rerank ON — the opposite of what the
retrieval metrics (Eval B) predict. Two reasons, both worth recording:

1. **Within judge noise.** 72% vs 64% is 18 vs 16 of 25 scenarios — a 2-scenario
   swing from a stochastic LLM judge on a single run. Not a meaningful delta.
2. **`grounded` ≠ correct technique.** The criterion only checks that the reply
   names *a* real technique, which it nearly always does. It is largely
   insensitive to *which* technique was retrieved, so it cannot reflect the
   retrieval improvement Eval B measures directly.

**Conclusion:** the robust, reproducible before/after for this project is the
**Eval B retrieval hit-rate (0.76 → 0.96)** from fixing the reranker. Eval A
confirms reply quality is high across the board (specific/tone at 100%,
actionable ≥92%) but its single `grounded` bit is too coarse to serve as the
rerank before/after. A sharper future criterion would grade whether the reply
applies one of the scenario's *expected* techniques, not just any real one.
