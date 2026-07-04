"""Memory recall helpers with day-boundary awareness."""

from datetime import datetime

from app.config import get_app_timezone
from app.memory.client import mem_get_all, mem_search


def _relative_day_label(created_at_raw: str | datetime | None) -> str:
    """Convert a created_at timestamp to a relative day label for the agent.

    Returns labels like '[today]', '[yesterday]', '[2 days ago]', or
    '[Mon Jul 04]' for older memories. Returns empty string if the
    timestamp is missing or unparseable.
    """
    if not created_at_raw:
        return ""

    try:
        ts: datetime
        if isinstance(created_at_raw, datetime):
            ts = created_at_raw
        elif isinstance(created_at_raw, str):
            ts = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
        else:
            return ""

        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=get_app_timezone())

        mem_date = ts.astimezone(get_app_timezone()).date()
        today = datetime.now(get_app_timezone()).date()
        delta = (today - mem_date).days

        if delta == 0:
            return "[today]"
        elif delta == 1:
            return "[yesterday]"
        elif delta < 7:
            return f"[{delta} days ago]"
        else:
            return f"[{mem_date.strftime('%a %b %d')}]"
    except (ValueError, TypeError):
        return ""


def recall_history(query: str, telegram_user_id: int, limit: int = 5) -> str:
    """Return a compact relevant slice of history as a text string.

    Each entry is prefixed with a relative day label so the LLM can
    distinguish today's memories from yesterday's.
    """
    entries = mem_search(query, user_id=str(telegram_user_id), limit=limit)
    lines: list[str] = []
    for e in entries:
        memory = e.get("memory", "")
        if not memory:
            continue
        label = _relative_day_label(e.get("created_at"))
        entry = f"{label} {memory}".strip() if label else memory
        lines.append(entry)
    return "\n".join(lines)


def detect_patterns(telegram_user_id: int) -> str:
    """Fetch all memories (capped at 20) for pattern detection.

    Each entry is prefixed with a relative day label.
    """
    entries = mem_get_all(user_id=str(telegram_user_id))
    lines: list[str] = []
    for e in entries[:20]:
        memory = e.get("memory", "")
        if not memory:
            continue
        label = _relative_day_label(e.get("created_at"))
        entry = f"{label} {memory}".strip() if label else memory
        lines.append(entry)
    return "\n".join(lines)
