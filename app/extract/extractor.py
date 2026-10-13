from collections.abc import Sequence

from app.extract.schema import ExtractedFacts
from app.habits.plan import HabitPlanContext, render_habit_plan_for_prompt
from app.llm.client import complete

_BASE_SYSTEM = (
    "You are a structured-data extractor for a personal habit-tracking app. "
    "Given a user's daily log entry, extract habit-related facts. "
    "If a field is not mentioned, omit it (use null). "
    "adherence is yes/no/partial based on whether habits were completed. "
    "logged_date is the date the user is referring to in their message. "
    "Resolve relative phrases like 'yesterday', 'last Tuesday', 'on 3rd Jan' "
    "against the current date provided in the prompt. "
    "If no date is mentioned or implied, leave logged_date null. "
)


async def extract(
    log_text: str, habit_plans: Sequence[HabitPlanContext] | None = None
) -> ExtractedFacts:
    """Call the LLM and parse the result into ExtractedFacts."""
    response = await complete(
        messages=[{"role": "user", "content": log_text}],
        system=_build_system(habit_plans),
        max_tokens=512,
        output_format=ExtractedFacts,
    )
    if response.parsed_output is None:
        raise ValueError("model did not return structured output")
    return _filter_to_known_habits(response.parsed_output, habit_plans)


def _build_system(habit_plans: Sequence[HabitPlanContext] | None) -> str:
    from datetime import date as _date

    today = _date.today().isoformat()
    date_prefix = f"Current date: {today}. "
    if not habit_plans:
        return date_prefix + _BASE_SYSTEM + "habits should be a list of habit names."
    return (
        date_prefix + _BASE_SYSTEM + "Use only habit names from the user's habit plan below. "
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
