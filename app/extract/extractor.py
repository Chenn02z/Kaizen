from app.extract.schema import ExtractedFacts
from app.llm.client import complete

_SYSTEM = (
    "You are a structured-data extractor for a personal habit-tracking app. "
    "Given a user's daily log entry, extract habit-related facts using the provided tool. "
    "If a field is not mentioned, omit it (use null). "
    "habits should be a list of habit names (e.g. ['exercise', 'meditation']). "
    "adherence is yes/no/partial based on whether habits were completed. "
)

_TOOL = {
    "name": "extract_facts",
    "description": "Extract structured behavioral facts from the log entry.",
    "input_schema": ExtractedFacts.model_json_schema(),
}


async def extract(log_text: str) -> ExtractedFacts:
    """Call the LLM and parse the result into ExtractedFacts."""
    response = await complete(
        messages=[{"role": "user", "content": log_text}],
        system=_SYSTEM,
        tools=[_TOOL],
        max_tokens=512,
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "extract_facts":
            return ExtractedFacts.model_validate(block.input)
    raise ValueError("model did not return structured output")
