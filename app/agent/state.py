from typing import Any, Optional

from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    # Input fields
    event_kind: str  # "user_message" | "tick"
    telegram_user_id: int
    user_text: Optional[str]  # None on tick

    # Intermediate results
    facts: Optional[Any]  # ExtractedFacts | None
    retrieved_chunks: list[Any]  # list[CorpusChunk]
    history: str

    # Output fields
    decision: str  # "respond" | "silent"
    reply_text: Optional[str]
    technique: Optional[str]
    silence_reason: Optional[str]  # kept for backwards compat; use decision_reason
    decision_reason: Optional[str]  # model's stated reason (both respond and silent)
