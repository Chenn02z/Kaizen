"""AC: judge() returns a valid JudgeScore from a mocked complete() parsed response."""

from unittest.mock import AsyncMock, MagicMock

from evals.golden import Scenario
from evals.judge import JudgeScore, judge


def _make_parsed_response(input_data: dict) -> MagicMock:
    msg = MagicMock()
    msg.parsed_output = JudgeScore.model_validate(input_data)
    return msg


async def test_judge_returns_valid_score(monkeypatch) -> None:
    payload = {
        "specific": True,
        "grounded": True,
        "right_tone": True,
        "actionable": False,
        "rationale": "Good technique reference but no next step given.",
    }
    mock_complete = AsyncMock(return_value=_make_parsed_response(payload))
    monkeypatch.setattr("evals.judge.complete", mock_complete)

    scenario = Scenario(
        log="Went for a 30 min run this morning. Feeling great!",
        expected_techniques=["progress_tracking", "identity_based_habits"],
        ideal_notes="Affirm the streak, reinforce runner identity, suggest logging it.",
    )
    reply = "Great work on the run! You're building a runner identity. Keep the streak alive."

    result = await judge(scenario, reply)

    mock_complete.assert_called_once()
    assert isinstance(result, JudgeScore)
    assert result.specific is True
    assert result.grounded is True
    assert result.right_tone is True
    assert result.actionable is False
    assert "next step" in result.rationale
