from app.extract.schema import ExtractedFacts
from app.memory.client import mem_add


def _facts_to_text(facts: ExtractedFacts, log_text: str) -> str:
    parts = [f"User log: {log_text}"]
    if facts.habits:
        parts.append(f"Habits mentioned: {', '.join(facts.habits)}")
    if facts.adherence:
        parts.append(f"Adherence: {facts.adherence.value}")
    if facts.mood:
        parts.append(f"Mood: {facts.mood}")
    if facts.trigger:
        parts.append(f"Trigger: {facts.trigger}")
    if facts.context:
        parts.append(f"Context: {facts.context}")
    return ". ".join(parts)


def store_facts(facts: ExtractedFacts, log_text: str, telegram_user_id: int) -> None:
    """Write extracted facts into Mem0 (sync — called via run_in_executor)."""
    mem_add(_facts_to_text(facts, log_text), user_id=str(telegram_user_id))
