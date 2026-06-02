from app.memory.client import mem_get_all, mem_search


def recall_history(query: str, telegram_user_id: int, limit: int = 5) -> str:
    """Return a compact relevant slice of history as a text string."""
    entries = mem_search(query, user_id=str(telegram_user_id), limit=limit)
    return "\n".join(e["memory"] for e in entries if "memory" in e)


def detect_patterns(telegram_user_id: int) -> str:
    """Fetch all memories (capped at 20) for pattern detection."""
    entries = mem_get_all(user_id=str(telegram_user_id))
    return "\n".join(e["memory"] for e in entries[:20] if "memory" in e)
