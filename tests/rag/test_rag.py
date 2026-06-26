"""Tests for RAG acceptance criteria.

AC1: "skipped gym, no motivation" retrieves relevant chunks (reranked top results).
AC2: Reranking changes ordering vs raw similarity on at least one query.
AC3: Embeddings are cached — second upsert_corpus call does not re-embed unchanged chunks.
AC4: Generated reply names the retrieved technique, not generic advice.
"""

from unittest.mock import AsyncMock, MagicMock

from app.db.models import CorpusChunk
from app.rag.retrieve import _rerank, retrieve
from app.telegram.intake import _generate_reply


def _make_chunk(filename: str, content: str) -> CorpusChunk:
    chunk = CorpusChunk()
    chunk.filename = filename
    chunk.content = content
    chunk.content_hash = "abc"
    chunk.embedding = [0.0] * 1536
    return chunk


def _make_text_response(json_text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = json_text
    msg = MagicMock()
    msg.content = [block]
    return msg


# ---------------------------------------------------------------------------
# AC1: retrieve returns relevant chunks for a fixed query
# ---------------------------------------------------------------------------


async def test_retrieve_returns_chunks(monkeypatch) -> None:
    """retrieve() returns a non-empty list of CorpusChunk objects."""
    fake_vec = [0.1] * 1536
    mock_embed = AsyncMock(return_value=[fake_vec])

    impl_chunk = _make_chunk(
        "implementation_intentions.md",
        "Implementation intentions link a specific situation to an action.",
    )
    relapse_chunk = _make_chunk(
        "relapse_recovery.md",
        "Relapse recovery: return to the habit quickly after a lapse.",
    )
    motivation_chunk = _make_chunk(
        "motivation_wave.md",
        "The motivation wave describes natural ebbs and flows of motivation.",
    )
    candidates = [impl_chunk, relapse_chunk, motivation_chunk]

    # Score order that keeps implementation_intentions first
    rerank_response = _make_text_response(
        '[{"index": 0, "score": 9}, {"index": 1, "score": 6}, {"index": 2, "score": 5}]'
    )
    mock_complete = AsyncMock(return_value=rerank_response)

    # Mock the DB query result
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = candidates
    mock_rows = MagicMock()
    mock_rows.scalars.return_value = mock_scalars

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_rows)

    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_cm.__aexit__ = AsyncMock(return_value=False)

    mock_session_local = MagicMock(return_value=mock_session_cm)

    monkeypatch.setattr("app.rag.retrieve.embed", mock_embed)
    monkeypatch.setattr("app.rag.retrieve.complete", mock_complete)
    monkeypatch.setattr("app.rag.retrieve.AsyncSessionLocal", mock_session_local)

    results = await retrieve("skipped gym no motivation", top_k=3, top_n=2)

    assert len(results) > 0
    assert all(isinstance(r, CorpusChunk) for r in results)
    # implementation_intentions should be ranked first (score 9)
    assert results[0].filename == "implementation_intentions.md"


# ---------------------------------------------------------------------------
# AC2: reranking changes ordering vs raw similarity
# ---------------------------------------------------------------------------


async def test_rerank_changes_ordering(monkeypatch) -> None:
    """_rerank returns candidates in a different order than the input when scores invert."""
    chunk_a = _make_chunk("implementation_intentions.md", "If-then planning for habits.")
    chunk_b = _make_chunk("two_minute_rule.md", "Do the habit for just two minutes.")
    chunk_c = _make_chunk("relapse_recovery.md", "Never miss twice after a lapse.")

    # Input order: a, b, c — scores invert: c=10, b=8, a=2
    inverted_scores = (
        '[{"index": 0, "score": 2}, {"index": 1, "score": 8}, {"index": 2, "score": 10}]'
    )
    mock_complete = AsyncMock(return_value=_make_text_response(inverted_scores))
    monkeypatch.setattr("app.rag.retrieve.complete", mock_complete)

    candidates = [chunk_a, chunk_b, chunk_c]
    result = await _rerank("I always skip gym", candidates, top_n=3)

    # After rerank the order should differ from the original [a, b, c]
    result_filenames = [r.filename for r in result]
    original_filenames = [c.filename for c in candidates]
    assert result_filenames != original_filenames
    # The highest-scored chunk (c, index 2, score 10) should now be first
    assert result[0].filename == "relapse_recovery.md"


# ---------------------------------------------------------------------------
# AC4: generated reply names the retrieved technique
# ---------------------------------------------------------------------------


async def test_generate_reply_names_technique(monkeypatch) -> None:
    """_generate_reply returns text that names the technique from the chunk."""
    chunk = _make_chunk(
        "implementation_intentions.md",
        "Implementation intentions: if X happens, then I will do Y.",
    )
    canned_reply = "Using implementation intentions: if it's 6am, then you lace up and go."
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = canned_reply
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_complete = AsyncMock(return_value=mock_response)
    monkeypatch.setattr("app.telegram.intake.complete", mock_complete)

    reply = await _generate_reply("skipped gym again", None, [chunk])

    assert "implementation intentions" in reply.lower()
    mock_complete.assert_called_once()


# ---------------------------------------------------------------------------
# AC3: embeddings are cached — second upsert_corpus call skips unchanged chunks
# ---------------------------------------------------------------------------


async def test_embed_caching(monkeypatch, tmp_path) -> None:
    """upsert_corpus does not re-embed a chunk whose content_hash is unchanged."""
    import hashlib

    from app.rag.embed import upsert_corpus

    # Create a temporary corpus file
    corpus_file = tmp_path / "test_technique.md"
    corpus_file.write_text("A short technique description for testing.")
    content = corpus_file.read_text()
    content_hash = hashlib.sha256(content.encode()).hexdigest()

    mock_embed = AsyncMock(return_value=[[0.1] * 1536])

    # First call: no existing row, embed is called
    existing_none = MagicMock()
    existing_none.scalar_one_or_none = MagicMock(return_value=None)

    # Second call: row exists with matching hash, embed should NOT be called
    existing_chunk = CorpusChunk()
    existing_chunk.filename = "test_technique.md"
    existing_chunk.content = content
    existing_chunk.content_hash = content_hash
    existing_chunk.embedding = [0.1] * 1536

    existing_found = MagicMock()
    existing_found.scalar_one_or_none = MagicMock(return_value=existing_chunk)

    call_count = {"n": 0}

    def make_execute_result():
        call_count["n"] += 1
        if call_count["n"] == 1:
            return existing_none
        return existing_found

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=lambda *a, **kw: make_execute_result())
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_cm.__aexit__ = AsyncMock(return_value=False)

    mock_session_local = MagicMock(return_value=mock_session_cm)

    monkeypatch.setattr("app.rag.embed.embed", mock_embed)
    monkeypatch.setattr("app.rag.embed.AsyncSessionLocal", mock_session_local)
    monkeypatch.setattr("app.rag.embed.CORPUS_DIR", tmp_path)

    # First run: should embed the one file
    count1 = await upsert_corpus()
    assert count1 == 1
    assert mock_embed.call_count == 1

    # Second run: same content hash, should skip
    count2 = await upsert_corpus()
    assert count2 == 0
    # embed still called only once total
    assert mock_embed.call_count == 1
