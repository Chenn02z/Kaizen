from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Literal, Protocol, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_app_timezone
from app.habits.evidence import (
    EffectiveHabitState,
    build_effective_evidence_ledger,
    is_positive_status,
)

HabitDayStatus = Literal["done", "missing", "not_due", "unknown"]
AgentHabitStatus = Literal["done", "missing", "not_due"]

_DEFAULT_WINDOW = "20:00"
_WEEKDAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_CHECKIN_ANSWER_REASON_PREFIX = "check-in answer"


class HabitPlanRead(Protocol):
    category_name: str
    habit_name: str
    cadence_type: str
    cadence_value: Any
    success_condition: str
    fallback_checkin_enabled: bool
    expected_evidence_window: str | None


@dataclass(frozen=True)
class HabitReadState:
    habit_name: str
    category_name: str
    success_condition: str
    cadence_type: str
    cadence_value: Any
    weekly_positive_count: int
    effective_state: EffectiveHabitState | None
    cadence_due_today: bool
    due_reason: str | None
    fallback_checkin_due: bool
    day_status: HabitDayStatus
    agent_status: AgentHabitStatus
    is_corrected: bool
    is_checkin_answer: bool


async def get_habit_day_states(
    session: AsyncSession,
    telegram_user_id: int,
    plans: Sequence[HabitPlanRead],
    now: datetime | None = None,
) -> list[HabitReadState]:
    current = _app_datetime(now)
    target_day = current.date()
    ledger = await build_effective_evidence_ledger(
        session,
        telegram_user_id,
        start_date=_week_start(target_day),
        end_date=target_day,
    )
    today_states = ledger.states_by_date.get(target_day, {})
    weekly_counts = weekly_positive_counts(ledger.states_by_date)

    return [
        _build_habit_read_state(
            plan,
            target_day,
            current.time(),
            today_states.get(plan.habit_name),
            weekly_counts.get(plan.habit_name, 0),
        )
        for plan in plans
    ]


async def get_due_habits(
    session: AsyncSession,
    telegram_user_id: int,
    plans: Sequence[HabitPlanRead],
    now: datetime | None = None,
) -> list[HabitReadState]:
    current = _app_datetime(now)
    rows = await get_habit_day_states(session, telegram_user_id, plans, current)
    return [row for row in rows if row.fallback_checkin_due]


async def get_dashboard_habit_rows(
    session: AsyncSession,
    telegram_user_id: int,
    plans: Sequence[HabitPlanRead],
    now: datetime | None = None,
) -> list[HabitReadState]:
    return await get_habit_day_states(session, telegram_user_id, plans, now)


async def build_agent_habit_summary(
    session: AsyncSession,
    telegram_user_id: int,
    plans: Sequence[HabitPlanRead],
    now: datetime | None = None,
) -> str:
    rows = await get_habit_day_states(session, telegram_user_id, plans, now)
    lines = [
        f"- {row.habit_name}: {row.agent_status}{' corrected' if row.is_corrected else ''}"
        for row in rows
    ]
    return "\n".join(lines) if lines else "No habit state available."


def weekly_positive_counts(
    states_by_date: dict[date, dict[str, EffectiveHabitState]],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for day_states in states_by_date.values():
        for state in day_states.values():
            if not is_positive_status(state.status):
                continue
            counts[state.habit_name] = counts.get(state.habit_name, 0) + 1
    return counts


def habit_due_today(plan: HabitPlanRead, today: date, weekly_completed: int) -> bool:
    if plan.cadence_type == "daily":
        return True
    if plan.cadence_type == "specific_weekdays":
        values = plan.cadence_value if isinstance(plan.cadence_value, list) else []
        return _WEEKDAY_KEYS[today.weekday()] in values
    if plan.cadence_type == "times_per_week":
        target = int(plan.cadence_value or 0)
        if target <= 0:
            return False
        remaining_needed = max(0, target - weekly_completed)
        days_remaining_after_today = 6 - today.weekday()
        return remaining_needed > days_remaining_after_today
    return False


def fallback_window_has_arrived(current: datetime, expected_window: str | None = None) -> bool:
    return _app_datetime(current).time() >= _parse_window(expected_window or _DEFAULT_WINDOW)


def _build_habit_read_state(
    plan: HabitPlanRead,
    target_day: date,
    current_time: time,
    effective_state: EffectiveHabitState | None,
    weekly_positive_count: int,
) -> HabitReadState:
    positive = effective_state is not None and is_positive_status(effective_state.status)
    is_checkin_answer = _is_checkin_answer_state(effective_state)
    due_reason = _due_reason(plan, target_day, weekly_positive_count)
    cadence_due = due_reason is not None

    if positive:
        day_status: HabitDayStatus = "done"
        agent_status: AgentHabitStatus = "done"
    elif cadence_due:
        window = _parse_window(plan.expected_evidence_window)
        day_status = "missing" if current_time >= window else "unknown"
        agent_status = "missing"
    else:
        day_status = "not_due"
        agent_status = "not_due"

    fallback_checkin_due = (
        plan.fallback_checkin_enabled
        and cadence_due
        and not positive
        and not is_checkin_answer
        and current_time >= _parse_window(plan.expected_evidence_window)
    )
    return HabitReadState(
        habit_name=plan.habit_name,
        category_name=plan.category_name,
        success_condition=plan.success_condition,
        cadence_type=plan.cadence_type,
        cadence_value=plan.cadence_value,
        weekly_positive_count=weekly_positive_count,
        effective_state=effective_state,
        cadence_due_today=cadence_due,
        due_reason=due_reason,
        fallback_checkin_due=fallback_checkin_due,
        day_status=day_status,
        agent_status=agent_status,
        is_corrected=bool(effective_state.corrected) if effective_state else False,
        is_checkin_answer=is_checkin_answer,
    )


def _due_reason(plan: HabitPlanRead, today: date, weekly_completed: int) -> str | None:
    if not habit_due_today(plan, today, weekly_completed):
        return None
    if plan.cadence_type == "daily":
        return "daily habit has no completion evidence today"
    if plan.cadence_type == "specific_weekdays":
        return "weekday habit has no completion evidence today"
    if plan.cadence_type == "times_per_week":
        target = int(plan.cadence_value or 0)
        return f"weekly target needs completion today ({weekly_completed}/{target} done)"
    return None


def _is_checkin_answer_state(state: EffectiveHabitState | None) -> bool:
    reason = getattr(state, "reason", None)
    return isinstance(reason, str) and reason.startswith(_CHECKIN_ANSWER_REASON_PREFIX)


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _parse_window(value: str | None) -> time:
    if not value:
        return time(hour=20)
    hour, minute = value.split(":", maxsplit=1)
    return time(hour=int(hour), minute=int(minute))


def _app_datetime(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(get_app_timezone())
    if value.tzinfo is None:
        return value.replace(tzinfo=get_app_timezone())
    return value.astimezone(get_app_timezone())
