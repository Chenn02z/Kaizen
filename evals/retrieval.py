"""Retrieval metrics for the Kaizen RAG pipeline.

Runs retrieve() against the golden set and reports recall@k, MRR, and
hit-rate.  Requires live DB + embedding API — do NOT import this from tests.

Usage:
    # rerank ON (default)
    uv run python -m evals.retrieval

    # rerank OFF
    uv run python -m evals.retrieval --no-rerank
"""

from __future__ import annotations

import asyncio
import sys

from app.rag.retrieve import retrieve
from evals.golden import GOLDEN_SET


async def _run_metrics(
    rerank: bool, top_k: int = 5, top_n: int = 3
) -> dict[str, float | int | bool]:
    """Return recall@k, MRR, and hit-rate across the golden set.

    Definitions:
    - hit:        at least one expected_technique appears in the top_n results
    - hit-rate:   fraction of scenarios that are a hit
    - recall@k:   fraction of expected techniques found in top_n results,
                  averaged across scenarios
    - MRR:        mean reciprocal rank of the first expected technique hit
                  in the top_n result list (0 if none found)
    """
    hits = 0
    recall_scores: list[float] = []
    reciprocal_ranks: list[float] = []

    for scenario in GOLDEN_SET:
        chunks = await retrieve(scenario.log, top_k=top_k, top_n=top_n, rerank=rerank)
        returned_stems = [c.filename.removesuffix(".md") for c in chunks]

        expected = set(scenario.expected_techniques)

        # recall@k for this scenario
        found = expected & set(returned_stems)
        recall = len(found) / len(expected) if expected else 0.0
        recall_scores.append(recall)

        # hit-rate
        if found:
            hits += 1

        # MRR: first position (1-indexed) where an expected technique appears
        rr = 0.0
        for rank, stem in enumerate(returned_stems, start=1):
            if stem in expected:
                rr = 1.0 / rank
                break
        reciprocal_ranks.append(rr)

    n = len(GOLDEN_SET)
    metrics = {
        "scenarios": n,
        "top_k": top_k,
        "top_n": top_n,
        "rerank": rerank,
        "hit_rate": round(hits / n, 4),
        "recall_at_k": round(sum(recall_scores) / n, 4),
        "mrr": round(sum(reciprocal_ranks) / n, 4),
    }
    return metrics


def main() -> None:
    rerank = "--no-rerank" not in sys.argv
    metrics = asyncio.run(_run_metrics(rerank=rerank))
    label = "rerank=ON" if rerank else "rerank=OFF"
    print(f"\n=== Retrieval metrics ({label}) ===")
    for key, val in metrics.items():
        print(f"  {key}: {val}")
    print()


if __name__ == "__main__":
    main()
