"""Runner functions: entry points for user messages and scheduled ticks."""

import logging
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import func, select, text

from app.agent.graph import get_graph
from app.db.models import Intervention
from app.db.session import AsyncSessionLocal
from app.habits.plan import (
    build_fallback_checkin_message,
    due_habits_missing_evidence,
    has_fallback_checkin_today,
)
from app.telegram.client import send_message

logger = logging.getLogger(__name__)

_DAILY_CAP = 1


async def run_user_message(
    telegram_user_id: int,
    user_text: str,
    facts: Optional[Any] = None,
) -> str:
    """Run the agent loop for an inbound user message and return the reply text.

    Pass pre-extracted *facts* to skip the extraction node (avoids double LLM call
    when the webhook has already run extraction for persistence purposes).
    """
    graph = get_graph()
    initial_state = {
        "event_kind": "user_message",
        "telegram_user_id": telegram_user_id,
        "user_text": user_text,
        "facts": facts,
        "retrieved_chunks": [],
        "history": "",
        "decision": "respond",
        "reply_text": user_text,
        "technique": None,
        "silence_reason": None,
    }
    final_state = await graph.ainvoke(initial_state)
    return final_state.get("reply_text") or user_text


async def run_tick(telegram_user_id: int, now: datetime | None = None) -> None:
    """Scheduled tick: decide whether to send a proactive nudge.

    A single transaction is held for the entire tick — from advisory lock
    acquisition through outcome insertion. This prevents two concurrent ticks
    from both passing the daily-cap check before either inserts its row.

    send_message is intentionally called after the transaction commits: it is
    an external HTTP call and must not hold a DB connection open.
    """
    decision: str = "silent"
    reply_text: str | None = None
    checkin_text: str | None = None

    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Advisory lock held for the full transaction duration.
            await session.execute(
                text("SELECT pg_advisory_xact_lock(:uid)"),
                {"uid": telegram_user_id},
            )

            today = now.date() if now else date.today()
            count_result = await session.execute(
                select(func.count())
                .select_from(Intervention)
                .where(
                    Intervention.telegram_user_id == telegram_user_id,
                    Intervention.kind == "proactive",
                    func.date(Intervention.created_at) == today,
                )
            )
            proactive_today = count_result.scalar_one()

            if proactive_today >= _DAILY_CAP:
                session.add(
                    Intervention(
                        telegram_user_id=telegram_user_id,
                        kind="silence",
                        reason="daily cap reached",
                    )
                )
                logger.info("tick: daily cap reached for user %s", telegram_user_id)
                # transaction commits on context-manager exit; lock released then
                return

            due_habits = await due_habits_missing_evidence(session, telegram_user_id, now)
            if due_habits and not await has_fallback_checkin_today(
                session, telegram_user_id, today=(now.date() if now else None)
            ):
                checkin_text = build_fallback_checkin_message(due_habits)
                session.add(
                    Intervention(
                        telegram_user_id=telegram_user_id,
                        kind="check-in",
                        reason=(
                            "fallback check-in: missing evidence for "
                            + ", ".join(habit.habit_name for habit in due_habits)
                        ),
                        message=checkin_text,
                    )
                )
                logger.info("tick: fallback check-in for user %s", telegram_user_id)
            else:
                # Graph runs inside the transaction so the lock is still held.
                graph = get_graph()
                initial_state = {
                    "event_kind": "tick",
                    "telegram_user_id": telegram_user_id,
                    "user_text": None,
                    "facts": None,
                    "retrieved_chunks": [],
                    "history": "",
                    "decision": "silent",
                    "reply_text": None,
                    "technique": None,
                    "silence_reason": None,
                    "decision_reason": None,
                }
                try:
                    final_state = await graph.ainvoke(initial_state)
                except Exception:
                    logger.exception("tick: graph invocation failed for user %s", telegram_user_id)
                    session.add(
                        Intervention(
                            telegram_user_id=telegram_user_id,
                            kind="silence",
                            reason="graph error",
                        )
                    )
                    return

                decision = final_state.get("decision", "silent")
                reply_text = final_state.get("reply_text")
                technique = final_state.get("technique")
                reason = (
                    final_state.get("decision_reason")
                    or final_state.get("silence_reason")
                    or "agent decision"
                )

                session.add(
                    Intervention(
                        telegram_user_id=telegram_user_id,
                        kind="proactive" if decision == "respond" else "silence",
                        reason=reason,
                        technique=technique if decision == "respond" else None,
                        message=reply_text if decision == "respond" else None,
                    )
                )
        # transaction commits here; advisory lock released

    # send_message is outside the transaction — no DB connection held
    if checkin_text:
        try:
            await send_message(chat_id=telegram_user_id, text=checkin_text)
        except Exception:
            logger.exception("tick: send_message failed for user %s", telegram_user_id)
        return

    if decision == "respond" and reply_text:
        try:
            await send_message(chat_id=telegram_user_id, text=reply_text)
        except Exception:
            logger.exception("tick: send_message failed for user %s", telegram_user_id)
