"""Eval A runner — reply quality (LLM-as-judge).

For each scenario in the golden set:
  1. Retrieve corpus chunks (rerank lever controlled by --no-rerank flag).
  2. Generate a coach reply via compose_log_reply.
  3. Score the reply with the LLM judge.

Aggregate and print per-criterion pass rates + headline grounded-response rate.

Usage:
    uv run python -m evals.runner            # rerank ON (default)
    uv run python -m evals.runner --no-rerank  # rerank OFF

This is a plain script — it makes real API calls and MUST NOT run under pytest.
"""

from __future__ import annotations

import asyncio
import sys

from app.rag.replies import compose_log_reply
from app.rag.retrieve import retrieve
from evals.golden import GOLDEN_SET
from evals.judge import JudgeScore, judge


async def _run(rerank: bool) -> dict[str, float]:
    """Score every scenario and return aggregate metrics."""
    totals: dict[str, int] = {
        "specific": 0,
        "grounded": 0,
        "right_tone": 0,
        "actionable": 0,
    }
    n = len(GOLDEN_SET)

    for i, scenario in enumerate(GOLDEN_SET, start=1):
        print(f"  [{i}/{n}] scoring: {scenario.log[:60]!r}...")
        chunks = await retrieve(scenario.log, rerank=rerank)
        reply = await compose_log_reply(scenario.log, None, chunks)
        score: JudgeScore = await judge(scenario, reply)

        if score.specific:
            totals["specific"] += 1
        if score.grounded:
            totals["grounded"] += 1
        if score.right_tone:
            totals["right_tone"] += 1
        if score.actionable:
            totals["actionable"] += 1

    return {k: round(v / n, 4) for k, v in totals.items()}


def _print_table(metrics: dict[str, float], rerank: bool) -> None:
    label = "rerank=ON" if rerank else "rerank=OFF"
    print(f"\n=== Eval A — Reply quality ({label}, n={len(GOLDEN_SET)}) ===")
    print(f"  {'criterion':<15} {'pass-rate':>10}")
    print(f"  {'-'*15} {'-'*10}")
    for criterion, rate in metrics.items():
        pct = f"{rate * 100:.1f}%"
        print(f"  {criterion:<15} {pct:>10}")
    grounded_rate = metrics["grounded"]
    print(f"\n  Headline — grounded-response rate: {grounded_rate * 100:.1f}%")
    print()


def main() -> None:
    rerank = "--no-rerank" not in sys.argv
    print(f"Running Eval A with rerank={'ON' if rerank else 'OFF'} ...")
    metrics = asyncio.run(_run(rerank=rerank))
    _print_table(metrics, rerank)


if __name__ == "__main__":
    main()
