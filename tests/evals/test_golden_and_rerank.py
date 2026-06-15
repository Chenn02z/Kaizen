"""Eval acceptance-criterion tests — no real API calls.

AC-golden: every expected_technique in the golden set maps to a real corpus file.
AC-rerank:  retrieve(..., rerank=False) skips _rerank/complete and returns <= top_n chunks.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from evals.golden import GOLDEN_SET

CORPUS_DIR = Path(__file__).parents[2] / "corpus"


# ---------------------------------------------------------------------------
# AC-golden: golden set integrity
# ---------------------------------------------------------------------------


def test_golden_techniques_exist_in_corpus() -> None:
    """Every expected_technique stem must match a real corpus/*.md file."""
    existing_stems = {p.stem for p in CORPUS_DIR.glob("*.md")}
    missing: list[str] = []
    for scenario in GOLDEN_SET:
        for technique in scenario.expected_techniques:
            if technique not in existing_stems:
                missing.append(f"{technique!r} (log: {scenario.log[:40]!r})")
    assert not missing, "Techniques not in corpus:\n" + "\n".join(missing)


# ---------------------------------------------------------------------------
# AC-rerank: rerank=False skips _rerank and returns <= top_n chunks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieve_rerank_false_skips_llm(monkeypatch) -> None:
    """When rerank=False, complete() must not be called and len(result) <= top_n."""
    from app.db.models import CorpusChunk
    from app.rag.retrieve import retrieve

    def _make_chunk(name: str) -> CorpusChunk:
        c = CorpusChunk()
        c.filename = f"{name}.md"
        c.content = "some content"
        c.content_hash = "abc"
        c.embedding = [0.0] * 1536
        return c

    candidates = [_make_chunk(n) for n in ["a", "b", "c", "d", "e"]]

    mock_embed = AsyncMock(return_value=[[0.1] * 1536])
    mock_complete = AsyncMock()  # must NOT be called

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = candidates
    mock_rows = MagicMock()
    mock_rows.scalars.return_value = mock_scalars

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_rows)

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    monkeypatch.setattr("app.rag.retrieve.embed", mock_embed)
    monkeypatch.setattr("app.rag.retrieve.complete", mock_complete)
    monkeypatch.setattr("app.rag.retrieve.AsyncSessionLocal", MagicMock(return_value=mock_cm))

    top_n = 3
    results = await retrieve("some query", top_k=5, top_n=top_n, rerank=False)

    mock_complete.assert_not_called()
    assert len(results) <= top_n
