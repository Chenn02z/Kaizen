"""Tests for the memory module (AC1–AC3 from milestone 05-memory)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

USER_ID = 42


# ---------------------------------------------------------------------------
# AC1: recall_history returns relevant past events without returning everything
# ---------------------------------------------------------------------------


def test_recall_history_returns_bounded_relevant_subset(monkeypatch):
    """recall_history returns only the searched entries, not all 10 fixture entries."""
    # 10 "stored" entries; Mem0 search returns only 3 relevant ones
    all_memories = [{"memory": f"entry {i}"} for i in range(10)]
    relevant = all_memories[:3]

    with patch("app.memory.recall.mem_search", return_value=relevant):
        from app.memory.recall import recall_history

        result = recall_history("exercise", USER_ID, limit=5)

    # Contains each of the 3 returned entries
    for entry in relevant:
        assert entry["memory"] in result

    # Does NOT contain entries 3-9 (the ones search didn't return)
    for entry in all_memories[3:]:
        assert entry["memory"] not in result


# ---------------------------------------------------------------------------
# AC2: "When do I usually slip?" yields answer derived from planted pattern
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_answer_reflection_uses_planted_pattern(monkeypatch):
    """Reflection answer references the planted 'work stress' pattern."""
    # Fake complete returns an answer referencing work stress
    fake_block = MagicMock()
    fake_block.type = "text"
    fake_block.text = "You tend to skip exercise on high work stress days."
    fake_response = MagicMock()
    fake_response.content = [fake_block]

    with (
        patch(
            "app.telegram.intake.recall_history",
            return_value="skipped exercise, trigger: work stress",
        ),
        patch(
            "app.telegram.intake.detect_patterns",
            return_value="skipped exercise, trigger: work stress",
        ),
        patch("app.telegram.intake.complete", new=AsyncMock(return_value=fake_response)),
    ):
        from app.telegram.intake import _answer_reflection

        reply = await _answer_reflection("when do I usually slip?", USER_ID)

    assert "work stress" in reply


# ---------------------------------------------------------------------------
# AC3: Context sent to model is bounded — memory summarizes rather than
#       dumping all rows
# ---------------------------------------------------------------------------


def test_detect_patterns_caps_at_20_entries(monkeypatch):
    """detect_patterns returns at most 20 entries even if Mem0 has 25."""
    entries_25 = [{"memory": f"entry {i}"} for i in range(25)]

    with patch("app.memory.recall.mem_get_all", return_value=entries_25):
        from app.memory.recall import detect_patterns

        result = detect_patterns(USER_ID)

    # At most 20 lines in the output
    lines = result.strip().splitlines()
    assert len(lines) <= 20


@pytest.mark.asyncio
async def test_answer_reflection_system_prompt_bounded(monkeypatch):
    """The system prompt passed to complete does not exceed 5000 chars."""
    captured_kwargs: dict = {}

    fake_block = MagicMock()
    fake_block.type = "text"
    fake_block.text = "Pattern summary."
    fake_response = MagicMock()
    fake_response.content = [fake_block]

    async def fake_complete(messages, *, system=None, max_tokens=1024, tools=None):
        captured_kwargs["system"] = system
        return fake_response

    # entries long enough to exceed 3000 chars before truncation
    history_lines = "\n".join([f"entry {i}: " + "x" * 100 for i in range(20)])
    patterns_lines = "\n".join([f"pattern {i}: " + "y" * 100 for i in range(20)])

    with (
        patch("app.telegram.intake.recall_history", return_value=history_lines),
        patch("app.telegram.intake.detect_patterns", return_value=patterns_lines),
        patch("app.telegram.intake.complete", new=fake_complete),
    ):
        from app.telegram.intake import _answer_reflection

        await _answer_reflection("how was my week?", USER_ID)

    assert captured_kwargs.get("system") is not None
    # system prompt = fixed prefix (~200 chars) + context capped at 3000 chars
    assert len(captured_kwargs["system"]) < 3500


@pytest.mark.asyncio
async def test_descriptive_reflection_does_not_retrieve_lessons(monkeypatch):
    fake_block = MagicMock()
    fake_block.type = "text"
    fake_block.text = "You usually skip gym after stressful work days."
    fake_response = MagicMock()
    fake_response.content = [fake_block]
    mock_retrieve = AsyncMock()

    with (
        patch(
            "app.telegram.intake.recall_history",
            return_value="skipped gym after stressful work",
        ),
        patch("app.telegram.intake.detect_patterns", return_value="gym slips after work stress"),
        patch("app.telegram.intake.tool_retrieve", mock_retrieve),
        patch("app.telegram.intake.complete", new=AsyncMock(return_value=fake_response)),
    ):
        from app.telegram.intake import _answer_reflection

        reply = await _answer_reflection("when do I usually skip gym?", USER_ID)

    assert "skip gym" in reply
    mock_retrieve.assert_not_awaited()


@pytest.mark.asyncio
async def test_coaching_reflection_retrieves_lessons_after_history(monkeypatch):
    captured: dict[str, str] = {}

    fake_block = MagicMock()
    fake_block.type = "text"
    fake_block.text = "Use implementation intentions after late work nights."
    fake_response = MagicMock()
    fake_response.content = [fake_block]

    async def fake_complete(messages, *, system=None, max_tokens=1024, tools=None):
        captured["system"] = system or ""
        return fake_response

    lesson = MagicMock()
    lesson.content = (
        "technique: implementation intentions\n"
        "lesson: pick the prompt before tomorrow's mood arrives."
    )
    mock_retrieve = AsyncMock(return_value=[lesson])

    with (
        patch(
            "app.telegram.intake.recall_history",
            return_value="missed gym after late work twice",
        ),
        patch("app.telegram.intake.detect_patterns", return_value="late work is the gym trigger"),
        patch("app.telegram.intake.tool_retrieve", mock_retrieve),
        patch("app.telegram.intake.complete", new=fake_complete),
    ):
        from app.telegram.intake import _answer_reflection

        reply = await _answer_reflection("what should I change tomorrow?", USER_ID)

    query = mock_retrieve.await_args.args[0]
    assert "what should I change tomorrow" in query
    assert "missed gym after late work" in query
    assert "late work is the gym trigger" in query
    assert "Retrieved self-authored lessons" in captured["system"]
    assert "implementation intentions" in captured["system"]
    assert "implementation intentions" in reply
