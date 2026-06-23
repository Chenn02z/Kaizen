"""LangGraph state machine for the Kaizen agent."""

import logging
from typing import Literal, Optional

from pydantic import BaseModel

from app.agent.state import AgentState
from app.agent.tools import tool_extract, tool_recall, tool_retrieve
from app.llm.client import complete

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic schema for the decide_intervention tool call
# ---------------------------------------------------------------------------


class DecideIntervention(BaseModel):
    action: Literal["respond", "silent"]
    reason: str
    technique: Optional[str] = None
    message: Optional[str] = None


_DECIDE_TOOL: dict = {
    "name": "decide_intervention",
    "description": (
        "Decide whether to send a proactive nudge to the user or stay silent. "
        "Choose 'silent' when the user is on track or there is nothing useful to add."
    ),
    "input_schema": DecideIntervention.model_json_schema(),
}

_DECIDE_SYSTEM = (
    "You are Kaizen, a proactive behavior-change coach. "
    "You receive the user's recent behavioral history and relevant techniques. "
    "Your job is to decide: does the user need a nudge RIGHT NOW, or are they on track? "
    "Choose 'silent' if the user is doing well, has already logged today, or if you have "
    "nothing grounded and specific to say. "
    "Choose 'respond' only if you see a clear pattern of drift that a specific technique "
    "can address. When responding, name the technique and write a concise message (2-3 sentences). "
    "Use the decide_intervention tool to record your decision."
)

_REPLY_SYSTEM = (
    "You are Kaizen, a personal behavior-change coach. "
    "Use ONLY the provided behavioral-science techniques to give a specific, actionable reply. "
    "Name the technique you are applying. Be concise (2-4 sentences). "
    "If the user's history shows a pattern relevant to this log, reference it."
)


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


def classify(state: AgentState) -> AgentState:
    """Route the event: user_message stays as-is; tick is already labelled."""
    # Nothing to compute; routing happens in the graph edge logic.
    return state


async def extract_facts(state: AgentState) -> AgentState:
    """Run the extractor and store results in state (user_message path only).

    If facts are already in state (pre-extracted by the webhook), skip the LLM call.
    """
    if state.get("facts") is not None:
        return state
    text = state.get("user_text") or ""
    try:
        facts = await tool_extract(text, state["telegram_user_id"])
    except Exception:
        logger.exception("extract_facts node failed")
        facts = None
    return {**state, "facts": facts}


async def retrieve_techniques(state: AgentState) -> AgentState:
    """RAG retrieval using the log text + habit names as the query."""
    facts = state.get("facts")
    user_text = state.get("user_text") or ""
    habit_str = " ".join(facts.habits) if facts and facts.habits else ""
    query = f"{user_text} {habit_str}".strip() or "behavior change habit"
    try:
        chunks = await tool_retrieve(query)
    except Exception:
        logger.exception("retrieve_techniques node failed")
        chunks = []
    return {**state, "retrieved_chunks": chunks}


async def recall(state: AgentState) -> AgentState:
    """Fetch memory summary for the user."""
    user_text = state.get("user_text") or "recent habits"
    telegram_user_id = state["telegram_user_id"]
    try:
        history = await tool_recall(user_text, telegram_user_id)
    except Exception:
        logger.exception("recall node failed")
        history = ""
    return {**state, "history": history}


async def decide(state: AgentState) -> AgentState:
    """Tick path: call the LLM to decide whether to send a proactive nudge."""
    history = state.get("history") or ""
    habit_state_summary = state.get("habit_state_summary") or ""
    chunks = state.get("retrieved_chunks") or []
    techniques_text = "\n\n---\n\n".join(c.content for c in chunks)

    # Bound the context sent to the model
    history_section = history[:2000]
    techniques_section = techniques_text[:2000]

    context = (
        f"Today's effective habit state:\n{habit_state_summary[:1000]}\n\n"
        f"User's recent behavioral history:\n{history_section}\n\n"
        f"Relevant behavioral-science techniques:\n{techniques_section}"
    )

    try:
        response = await complete(
            messages=[{"role": "user", "content": context}],
            system=_DECIDE_SYSTEM,
            tools=[_DECIDE_TOOL],
            max_tokens=512,
        )
        for block in response.content:
            if block.type == "tool_use" and block.name == "decide_intervention":
                decision = DecideIntervention.model_validate(block.input)
                return {
                    **state,
                    "decision": decision.action,
                    "reply_text": decision.message,
                    "technique": decision.technique,
                    "silence_reason": decision.reason if decision.action == "silent" else None,
                    "decision_reason": decision.reason,
                }
    except Exception:
        logger.exception("decide node failed; defaulting to silent")

    # Safe default: stay silent on any error
    return {
        **state,
        "decision": "silent",
        "silence_reason": "decide node error",
        "decision_reason": "decide node error",
    }


async def respond(state: AgentState) -> AgentState:
    """Compose the final reply for user_message path."""
    chunks = state.get("retrieved_chunks") or []
    history = state.get("history") or ""
    user_text = state.get("user_text") or ""

    if not chunks:
        return {**state, "reply_text": user_text, "decision": "respond"}

    context = "\n\n---\n\n".join(c.content for c in chunks)
    history_section = f"\n\nUser's recent history:\n{history[:1500]}" if history else ""
    system = f"{_REPLY_SYSTEM}\n\nTechniques available:\n\n{context}{history_section}"

    try:
        response = await complete(
            messages=[{"role": "user", "content": user_text}],
            system=system,
            max_tokens=300,
        )
        reply = next((b.text for b in response.content if b.type == "text"), user_text)
    except Exception:
        logger.exception("respond node failed")
        reply = user_text

    return {**state, "reply_text": reply, "decision": "respond"}


# ---------------------------------------------------------------------------
# Edge routing
# ---------------------------------------------------------------------------


def _after_classify(state: AgentState) -> str:
    if state.get("event_kind") == "user_message":
        return "extract_facts"
    return "recall"


def _after_recall(state: AgentState) -> str:
    if state.get("event_kind") == "tick":
        return "decide"
    return "respond"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------


def build_graph():  # type: ignore[return]
    """Construct and compile the LangGraph StateGraph."""
    from langgraph.graph import END, StateGraph

    g: StateGraph = StateGraph(AgentState)

    g.add_node("classify", classify)
    g.add_node("extract_facts", extract_facts)
    g.add_node("retrieve_techniques", retrieve_techniques)
    g.add_node("recall", recall)
    g.add_node("decide", decide)
    g.add_node("respond", respond)

    g.set_entry_point("classify")

    g.add_conditional_edges(
        "classify",
        _after_classify,
        {"extract_facts": "extract_facts", "recall": "recall"},
    )
    g.add_edge("extract_facts", "retrieve_techniques")
    g.add_edge("retrieve_techniques", "recall")
    g.add_conditional_edges(
        "recall",
        _after_recall,
        {"decide": "decide", "respond": "respond"},
    )
    g.add_edge("decide", END)
    g.add_edge("respond", END)

    return g.compile()


# Singleton compiled graph
_graph = None


def get_graph():  # type: ignore[return]
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
