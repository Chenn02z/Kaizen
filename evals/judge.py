"""LLM-as-judge for Kaizen reply quality (Eval A).

Scores a single (Scenario, generated_reply) pair on a 4-criterion rubric.
Each criterion is a boolean pass/fail; the judge also returns a short rationale.

Call through the LLM gateway — never import a vendor SDK here.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.llm.client import complete
from evals.golden import Scenario

_SYSTEM = (
    "You are a strict but fair grader for a behavior-change coaching AI. "
    "Score the reply on exactly four boolean criteria using the provided tool. "
    "Base your judgment on the grading reference supplied in the user message."
)

_RUBRIC = """\
Criteria:
- specific: The reply is concrete and tailored to THIS log entry — not generic advice \
that could apply to anyone.
- grounded: The reply names or clearly applies a real behavioral-science technique \
(e.g. habit stacking, if-then planning, urge surfing). The technique must exist in \
the literature; invented or vague labels do not count.
- right_tone: The reply is warm and supportive — coaching, not preachy or judgmental.
- actionable: The reply gives a clear next step the user can act on immediately or \
tomorrow.
"""


class JudgeScore(BaseModel):
    specific: bool
    grounded: bool
    right_tone: bool
    actionable: bool
    rationale: str


_TOOL: dict = {
    "name": "score_reply",
    "description": "Return pass/fail for each rubric criterion plus a brief rationale.",
    "input_schema": JudgeScore.model_json_schema(),
}


async def judge(scenario: Scenario, reply: str) -> JudgeScore:
    """Score *reply* against *scenario* using the LLM judge."""
    techs = scenario.expected_techniques
    expected = ", ".join(techs) if techs else "none specified"
    user_msg = (
        f"## Grading reference\n"
        f"Expected techniques: {expected}\n"
        f"Ideal-response notes: {scenario.ideal_notes}\n\n"
        f"{_RUBRIC}\n"
        f"## User log\n{scenario.log}\n\n"
        f"## Coach reply to grade\n{reply}"
    )
    response = await complete(
        messages=[{"role": "user", "content": user_msg}],
        system=_SYSTEM,
        tools=[_TOOL],
        max_tokens=512,
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "score_reply":
            return JudgeScore.model_validate(block.input)
    raise ValueError("judge model did not return structured output")
