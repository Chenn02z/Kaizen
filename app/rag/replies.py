"""Grounded reply composition for log responses and reflection answers."""

from __future__ import annotations

import asyncio
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.config import get_app_timezone
from app.db.models import CorpusChunk
from app.llm.client import complete
from app.memory.recall import detect_patterns, recall_history
from app.rag.retrieve import retrieve


class ReflectionMode(StrEnum):
    DESCRIPTIVE = "descriptive"
    COACHING = "coaching"


class LogReplyInput(BaseModel):
    log_text: str
    chunks: list[CorpusChunk]
    history: str = ""
    habit_state_summary: str = ""
    today_logs: str = ""
    facts: Any | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ReflectionInput(BaseModel):
    query: str
    telegram_user_id: int


_LOG_REPLY_SYSTEM = (
    "You are Kaizen, a personal behavior-change coach. "
    "Use only the provided behavioral-science techniques to give a specific, actionable reply. "
    "Name the technique you are applying. Keep it short enough to read at a glance in Telegram. "
    "If the user's history shows a pattern relevant to this log, reference it. "
    "Treat the provided habit state as source-of-truth for cadence targets "
    "and whether a habit is due today. "
    "Do not claim a target is missing if the habit state shows one. "
    "For weekly habits, do not imply the user must complete it today unless due_today=yes. "
    "If no provided technique fits the log, acknowledge the log from the user's history only "
    "and do not force a technique."
)

_COACHING_REFLECTION_SYSTEM = (
    "You are Kaizen, a personal behavior-change coach. "
    "Answer action-oriented reflection questions history-first: use the provided "
    "history and patterns as the reason for any advice. If a retrieved lesson fits "
    "that actual history, name its technique, apply one lesson, and explain why it "
    "fits this user's pattern. If no retrieved lesson fits, answer from history only "
    "and do not force a technique. Keep it short enough to read at a glance in Telegram."
)

_DESCRIPTIVE_REFLECTION_SYSTEM = (
    "You are Kaizen, a personal behavior-change coach. "
    "Answer the user's descriptive reflection question using only the provided "
    "history and patterns. Do not introduce lessons or techniques unless the user "
    "asks for a recommendation. Be specific and cite actual entries. Keep it short "
    "enough to read at a glance in Telegram."
)

_REFLECTION_PATTERNS = [
    "how was my week",
    "when do i",
    "how am i doing",
    "my patterns",
    "do i usually",
    "when do i slip",
    "when do i usually",
]

_COACHING_REFLECTION_PATTERNS = [
    "what should i change",
    "what should i do",
    "what can i change",
    "what can i do",
    "what should i try",
    "what should i do differently",
    "what do i change",
    "what do i try",
    "what to change",
    "what to try",
    "how do i stop",
    "how can i stop",
    "how should i stop",
    "how do i avoid",
    "how can i avoid",
    "how should i avoid",
    "change tomorrow",
    "try tomorrow",
    "do tomorrow",
    "differently tomorrow",
    "next time i",
]


def is_reflection_query(text: str) -> bool:
    lower = text.lower()
    return any(pattern in lower for pattern in _REFLECTION_PATTERNS) or (
        classify_reflection(text) == ReflectionMode.COACHING
    )


def classify_reflection(text: str) -> ReflectionMode:
    lower = text.lower()
    if any(pattern in lower for pattern in _COACHING_REFLECTION_PATTERNS):
        return ReflectionMode.COACHING
    return ReflectionMode.DESCRIPTIVE


async def compose_log_reply(
    log_text: str,
    facts: Any | None,
    chunks: list[CorpusChunk],
    history: str = "",
    habit_state_summary: str = "",
    today_logs: str = "",
) -> str:
    request = LogReplyInput(
        log_text=log_text,
        facts=facts,
        chunks=chunks,
        history=history,
        habit_state_summary=habit_state_summary,
        today_logs=today_logs,
    )
    if not request.chunks:
        return request.log_text

    context = _format_lessons(request.chunks, limit=2000)
    history_section = _format_history(request.history, limit=1500)
    today_logs_section = _format_today_logs(request.today_logs, limit=1000)
    habit_state_section = _format_habit_state(request.habit_state_summary, limit=1500)
    now = datetime.now(get_app_timezone())
    time_line = now.strftime("Current time: %H:%M (%Z). ")
    system = (
        f"{_LOG_REPLY_SYSTEM}\n\n"
        f"{time_line}Techniques available:\n\n{context}"
        f"{today_logs_section}{history_section}{habit_state_section}"
    )
    response = await complete(
        messages=[{"role": "user", "content": request.log_text}],
        system=system,
        max_tokens=300,
    )
    return _first_text(response)


async def answer_reflection(query: str, telegram_user_id: int) -> str:
    request = ReflectionInput(query=query, telegram_user_id=telegram_user_id)
    history = await asyncio.get_running_loop().run_in_executor(
        None, recall_history, request.query, request.telegram_user_id
    )
    patterns = await asyncio.get_running_loop().run_in_executor(
        None, detect_patterns, request.telegram_user_id
    )
    return await answer_reflection_from_history(
        query=request.query,
        history=history,
        patterns=patterns,
    )


async def answer_reflection_from_history(
    *,
    query: str,
    history: str,
    patterns: str,
) -> str:
    if not history and not patterns:
        return "I don't have enough history yet - keep logging and I'll start surfacing patterns!"

    context = _format_reflection_context(history=history, patterns=patterns)
    mode = classify_reflection(query)
    lesson_context = ""
    if mode == ReflectionMode.COACHING:
        lesson_query = build_lesson_query(query=query, history=history, patterns=patterns)
        chunks = await retrieve(lesson_query)
        if chunks:
            lessons = _format_lessons(chunks, limit=2000)
            lesson_context = f"\n\nRetrieved self-authored lessons:\n{lessons}"

    system_prompt = (
        _COACHING_REFLECTION_SYSTEM
        if mode == ReflectionMode.COACHING
        else _DESCRIPTIVE_REFLECTION_SYSTEM
    )
    response = await complete(
        messages=[{"role": "user", "content": query}],
        system=f"{system_prompt}\n\n{context}{lesson_context}",
        max_tokens=400,
    )
    return _first_text(response)


def build_lesson_query(*, query: str, history: str, patterns: str) -> str:
    """Build a lesson retrieval query from a reflection question plus real history."""
    history_part = history.strip()[:1200]
    pattern_part = patterns.strip()[:800]
    parts = [f"reflection question: {query.strip()}"]
    if history_part:
        parts.append(f"recent habit history: {history_part}")
    if pattern_part:
        parts.append(f"detected habit patterns: {pattern_part}")
    return "\n".join(parts)


def _format_today_logs(today_logs: str, *, limit: int) -> str:
    if not today_logs:
        return ""
    header = "\n\nToday's submitted logs (what the user has already logged today):\n"
    return f"{header}{today_logs[:limit]}"


def _format_lessons(chunks: list[CorpusChunk], *, limit: int) -> str:
    if not chunks:
        return "No retrieved lesson fit is available."
    return "\n\n---\n\n".join(chunk.content for chunk in chunks)[:limit]


def _format_history(history: str, *, limit: int) -> str:
    if not history:
        return ""
    return f"\n\nUser's recent history:\n{history[:limit]}"


def _format_habit_state(habit_state_summary: str, *, limit: int) -> str:
    if not habit_state_summary:
        return ""
    return f"\n\nCurrent habit state:\n{habit_state_summary[:limit]}"


def _format_reflection_context(*, history: str, patterns: str) -> str:
    if patterns:
        context = f"Recent relevant history:\n{history}\n\nAll patterns:\n{patterns}"
    else:
        context = f"Recent relevant history:\n{history}"
    return context[:3000]


def _first_text(response: Any) -> str:
    return next(block.text for block in response.content if block.type == "text")
