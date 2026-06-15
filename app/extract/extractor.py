from collections.abc import Sequence

from app.extract.schema import ExtractedFacts
from app.habits.plan import HabitPlanContext, render_habit_plan_for_prompt
from app.llm.client import complete

_BASE_SYSTEM = (
    "You are a structured-data extractor for a personal habit-tracking app. "
    "Given a user's daily log entry, extract habit-related facts using the provided tool. "
    "If a field is not mentioned, omit it (use null). "
    "adherence is yes/no/partial based on whether habits were completed. "
)

_TOOL = {
    "name": "extract_facts",
    "description": "Extract structured behavioral facts from the log entry.",
    "input_schema": ExtractedFacts.model_json_schema(),
}


async def extract(
    log_text: str, habit_plans: Sequence[HabitPlanContext] | None = None
) -> ExtractedFacts:
    """Call the LLM and parse the result into ExtractedFacts."""
    response = await complete(
        messages=[{"role": "user", "content": log_text}],
        system=_build_system(habit_plans),
        tools=[_TOOL],
        max_tokens=512,
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "extract_facts":
            facts = ExtractedFacts.model_validate(block.input)
            return _filter_to_known_habits(facts, habit_plans)
    raise ValueError("model did not return structured output")


def _build_system(habit_plans: Sequence[HabitPlanContext] | None) -> str:
    if not habit_plans:
        return _BASE_SYSTEM + "habits should be a list of habit names."
    return (
        _BASE_SYSTEM
        + "Use only habit names from the user's habit plan below. "
        "Habit aliases and success conditions are soft context for matching. "
        "If the log is ambiguous or does not clearly satisfy a known habit, leave habits empty. "
        "Do not invent new habit names.\n\n"
        f"User habit plan:\n{render_habit_plan_for_prompt(habit_plans)}"
    )


def _filter_to_known_habits(
    facts: ExtractedFacts, habit_plans: Sequence[HabitPlanContext] | None
) -> ExtractedFacts:
    if not habit_plans:
        return facts
    allowed = {plan.habit_name for plan in habit_plans}
    filtered = [habit for habit in facts.habits if habit in allowed]
    return facts.model_copy(update={"habits": filtered})
