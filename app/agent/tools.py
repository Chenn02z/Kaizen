"""Agent tools wrapping extract, RAG retrieve, and memory recall."""

import asyncio

from app.db.session import AsyncSessionLocal
from app.extract.extractor import extract as _extract
from app.habits.plan import get_habit_plan_context
from app.memory.recall import recall_history as _recall_history
from app.rag.retrieve import retrieve as _retrieve


async def tool_extract(log_text: str, telegram_user_id: int | None = None):  # type: ignore[return]
    """Extract structured facts from a log entry."""
    if telegram_user_id is None:
        return await _extract(log_text)
    async with AsyncSessionLocal() as session:
        habit_plans = await get_habit_plan_context(session, telegram_user_id)
        await session.commit()
    return await _extract(log_text, habit_plans)


async def tool_retrieve(query: str, top_k: int = 5, top_n: int = 3):  # type: ignore[return]
    """Retrieve relevant behavioral-science chunks for a query."""
    return await _retrieve(query, top_k=top_k, top_n=top_n)


async def tool_recall(query: str, telegram_user_id: int, limit: int = 5) -> str:
    """Return a compact relevant memory slice for the user."""
    return await asyncio.get_running_loop().run_in_executor(
        None, _recall_history, query, telegram_user_id, limit
    )
