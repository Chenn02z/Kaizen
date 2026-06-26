"""Runner functions: entry points for user messages and scheduled ticks."""

import logging
from datetime import date, datetime, time, timedelta
from typing import Any, Optional

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import get_graph
from app.agent.intervention_policy import (
    AgentInterventionDecision,
    InterventionDecision,
    InterventionPolicy,
    InterventionPolicyContext,
)
from app.config import get_app_timezone
from app.db.models import Intervention
from app.db.session import AsyncSessionLocal
from app.habits.plan import (
    due_habits_missing_evidence,
    get_habit_plan_context,
    has_fallback_checkin_today,
)
from app.habits.state import build_agent_habit_summary
from app.telegram.client import send_message

logger = logging.getLogger(__name__)

_DAILY_CAP = 4


def _app_day_bounds(now: datetime | None) -> tuple[date, datetime, datetime]:
    tz = get_app_timezone()
    reference = now.astimezone(tz) if now and now.tzinfo else now
    if reference is None:
        reference = datetime.now(tz)
    local_date = reference.date()
    day_start = datetime.combine(local_date, time.min, tzinfo=tz)
    day_end = day_start + timedelta(days=1)
    return local_date, day_start, day_end


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
        "lesson_query": None,
        "history": "",
        "habit_state_summary": "",
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
    policy_decision: InterventionDecision | None = None

    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Advisory lock held for the full transaction duration.
            await session.execute(
                text("SELECT pg_advisory_xact_lock(:uid)"),
                {"uid": telegram_user_id},
            )

            today, day_start, day_end = _app_day_bounds(now)
            count_result = await session.execute(
                select(func.count())
                .select_from(Intervention)
                .where(
                    Intervention.telegram_user_id == telegram_user_id,
                    Intervention.kind == "proactive",
                    Intervention.created_at >= day_start,
                    Intervention.created_at < day_end,
                )
            )
            proactive_today = count_result.scalar_one()

            if proactive_today >= _DAILY_CAP:
                due_habits = []
                has_checkin = False
                habit_state_summary = ""
            else:
                due_habits = await due_habits_missing_evidence(
                    session, telegram_user_id, now
                )
                has_checkin = await has_fallback_checkin_today(
                    session, telegram_user_id, today=today
                )
                habit_state_summary = await _build_habit_state_summary(
                    session, telegram_user_id, now
                )

            context = InterventionPolicyContext(
                telegram_user_id=telegram_user_id,
                local_date=today,
                day_start=day_start,
                day_end=day_end,
                proactive_count_today=proactive_today,
                daily_cap=_DAILY_CAP,
                due_habits_missing_evidence=due_habits,
                has_fallback_checkin_today=has_checkin,
                habit_state_summary=habit_state_summary,
            )

            policy = InterventionPolicy()
            policy_decision = await policy.decide(context, _run_graph_intervention_decider)

            session.add(
                Intervention(
                    telegram_user_id=telegram_user_id,
                    kind=policy_decision.intervention_kind,
                    reason=policy_decision.reason,
                    technique=policy_decision.technique
                    if policy_decision.action == "send_nudge"
                    else None,
                    message=policy_decision.message
                    if policy_decision.action in {"send_check_in", "send_nudge"}
                    else None,
                )
            )

            if policy_decision.source == "daily_cap":
                logger.info("tick: daily cap reached for user %s", telegram_user_id)
            elif policy_decision.action == "send_check_in":
                logger.info("tick: fallback check-in for user %s", telegram_user_id)
            else:
                logger.info(
                    "tick: policy decision for user %s: %s",
                    telegram_user_id,
                    policy_decision.action,
                )
        # transaction commits here; advisory lock released

    # send_message is outside the transaction — no DB connection held
    if policy_decision and policy_decision.should_send:
        try:
            await send_message(chat_id=telegram_user_id, text=policy_decision.message or "")
        except Exception:
            logger.exception("tick: send_message failed for user %s", telegram_user_id)


async def _run_graph_intervention_decider(
    context: InterventionPolicyContext,
) -> AgentInterventionDecision:
    # Graph runs inside the transaction so the advisory lock is still held.
    graph = get_graph()
    initial_state = {
        "event_kind": "tick",
        "telegram_user_id": context.telegram_user_id,
        "user_text": None,
        "facts": None,
        "retrieved_chunks": [],
        "lesson_query": None,
        "history": "",
        "habit_state_summary": context.habit_state_summary,
        "decision": "silent",
        "reply_text": None,
        "technique": None,
        "silence_reason": None,
        "decision_reason": None,
    }
    final_state = await graph.ainvoke(initial_state)
    return AgentInterventionDecision.from_agent_state(final_state)


async def _build_habit_state_summary(
    session: AsyncSession,
    telegram_user_id: int,
    now: datetime | None,
) -> str:
    plans = await get_habit_plan_context(session, telegram_user_id)
    return await build_agent_habit_summary(session, telegram_user_id, plans, now)
