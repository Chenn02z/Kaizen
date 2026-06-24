from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_app_timezone
from app.db.models import (
    ExtractedFacts,
    HabitCategory,
    HabitPlan,
    HabitProgress,
    Intervention,
    Log,
)
from app.gamification.stats import UserStats, get_user_stats
from app.habits.evidence import (
    EffectiveEvidenceLedger,
    build_effective_evidence_ledger,
    is_positive_status,
)
from app.habits.plan import HabitPlanContext, get_habit_plan_context, habit_due_today

DashboardHabitStatus = Literal["done", "missing", "not_due", "unknown"]


class DashboardHabit(BaseModel):
    name: str
    category: str
    level: int
    xp: int
    cadence_type: str
    cadence_value: Any = None
    success_condition: str
    today_status: DashboardHabitStatus
    is_corrected_today: bool = False


class DashboardLog(BaseModel):
    id: int
    text: str
    created_at: datetime
    habits: list[str]
    adherence: str | None = None
    mood: str | None = None
    trigger: str | None = None
    context: str | None = None
    corrected_habits: list[str] = []


class DashboardIntervention(BaseModel):
    id: int
    created_at: datetime
    kind: str
    reason: str
    technique: str | None = None
    message: str | None = None
    engaged: bool | None = None


class DashboardData(BaseModel):
    progress: UserStats
    habits: list[DashboardHabit]
    recent_logs: list[DashboardLog]
    recent_interventions: list[DashboardIntervention]


async def get_dashboard_data(
    telegram_user_id: int,
    session: AsyncSession,
    now: datetime | None = None,
) -> DashboardData:
    current = now or utcnow()
    await get_habit_plan_context(session, telegram_user_id)
    progress = await get_user_stats(telegram_user_id, session)
    plans = await _load_habit_plans(session, telegram_user_id)
    week_start = current.date() - timedelta(days=current.date().weekday())
    ledger = await build_effective_evidence_ledger(
        session,
        telegram_user_id,
        start_date=week_start,
        end_date=current.date(),
    )
    today_states = ledger.states_by_date.get(current.date(), {})
    week_counts = _count_positive_days(ledger)
    recent_logs = await _load_recent_logs(session, telegram_user_id)
    recent_corrections = await build_effective_evidence_ledger(session, telegram_user_id)
    recent_interventions = await _load_recent_interventions(session, telegram_user_id)

    return DashboardData(
        progress=progress,
        habits=[
            _build_habit_row(plan, habit_progress, current, today_states, week_counts)
            for plan, habit_progress in plans
        ],
        recent_logs=_attach_corrections_to_logs(recent_logs, recent_corrections),
        recent_interventions=recent_interventions,
    )


async def _load_habit_plans(
    session: AsyncSession, telegram_user_id: int
) -> list[tuple[HabitPlanContext, HabitProgress | None]]:
    result = await session.execute(
        select(HabitPlan, HabitCategory.name, HabitProgress)
        .join(HabitCategory, HabitCategory.id == HabitPlan.category_id)
        .outerjoin(
            HabitProgress,
            and_(
                HabitProgress.telegram_user_id == HabitPlan.telegram_user_id,
                HabitProgress.habit_name == HabitPlan.habit_name,
            ),
        )
        .where(HabitPlan.telegram_user_id == telegram_user_id)
        .order_by(HabitCategory.name, HabitPlan.habit_name)
    )
    rows: list[tuple[HabitPlanContext, HabitProgress | None]] = []
    for plan, category_name, habit_progress in result.all():
        rows.append(
            (
                HabitPlanContext(
                    category_name=category_name,
                    habit_name=plan.habit_name,
                    direction=plan.direction,
                    cadence_type=plan.cadence_type,
                    cadence_value=plan.cadence_value,
                    success_condition=plan.success_condition,
                    habit_aliases=plan.habit_aliases or [],
                    known_triggers=plan.known_triggers or [],
                    goal=plan.goal,
                    fallback_checkin_enabled=plan.fallback_checkin_enabled,
                    expected_evidence_window=plan.expected_evidence_window,
                ),
                habit_progress,
            )
        )
    return rows


async def _load_recent_logs(session: AsyncSession, telegram_user_id: int) -> list[DashboardLog]:
    result = await session.execute(
        select(Log, ExtractedFacts)
        .join(ExtractedFacts, ExtractedFacts.log_id == Log.id, isouter=True)
        .where(Log.telegram_user_id == telegram_user_id)
        .order_by(desc(Log.created_at))
        .limit(8)
    )
    items: list[DashboardLog] = []
    for log, facts in result.all():
        items.append(
            DashboardLog(
                id=log.id,
                text=log.text,
                created_at=log.created_at,
                habits=(facts.habits if facts else []) or [],
                adherence=facts.adherence if facts else None,
                mood=facts.mood if facts else None,
                trigger=facts.trigger if facts else None,
                context=facts.context if facts else None,
            )
        )
    return items


async def _load_recent_interventions(
    session: AsyncSession, telegram_user_id: int
) -> list[DashboardIntervention]:
    result = await session.execute(
        select(Intervention)
        .where(Intervention.telegram_user_id == telegram_user_id)
        .order_by(desc(Intervention.created_at))
        .limit(8)
    )
    return [
        DashboardIntervention(
            id=row.id,
            created_at=row.created_at,
            kind=row.kind,
            reason=row.reason,
            technique=row.technique,
            message=row.message,
            engaged=row.engaged,
        )
        for row in result.scalars().all()
    ]


def _build_habit_row(
    plan: HabitPlanContext,
    habit_progress: HabitProgress | None,
    now: datetime,
    today_states: dict[str, Any],
    week_counts: dict[str, int],
) -> DashboardHabit:
    today_state = today_states.get(plan.habit_name)
    done = today_state is not None and is_positive_status(today_state.status)
    due_today = habit_due_today(plan, now.date(), week_counts.get(plan.habit_name, 0))
    if done:
        status: DashboardHabitStatus = "done"
    elif due_today:
        window = _parse_window(plan.expected_evidence_window)
        status = "missing" if now.time() >= window else "unknown"
    else:
        status = "not_due"
    return DashboardHabit(
        name=plan.habit_name,
        category=plan.category_name,
        level=habit_progress.level if habit_progress else 1,
        xp=habit_progress.xp if habit_progress else 0,
        cadence_type=plan.cadence_type,
        cadence_value=plan.cadence_value,
        success_condition=plan.success_condition,
        today_status=status,
        is_corrected_today=bool(today_state.corrected) if today_state else False,
    )


def _attach_corrections_to_logs(
    logs: list[DashboardLog], ledger: EffectiveEvidenceLedger
) -> list[DashboardLog]:
    log_map = {
        entry.log_id: [state.habit_name for state in entry.effective_habits if state.corrected]
        for entry in ledger.logs
    }
    return [
        log.model_copy(update={"corrected_habits": log_map.get(log.id, [])})
        for log in logs
    ]


def _count_positive_days(ledger: EffectiveEvidenceLedger) -> dict[str, int]:
    counts: dict[str, int] = {}
    for day_states in ledger.states_by_date.values():
        for state in day_states.values():
            if not is_positive_status(state.status):
                continue
            counts[state.habit_name] = counts.get(state.habit_name, 0) + 1
    return counts


def _day_start(day: date) -> datetime:
    return datetime.combine(day, time.min).replace(tzinfo=timezone.utc)


def _parse_window(value: str | None) -> time:
    if not value:
        return time(hour=20)
    hour, minute = value.split(":", maxsplit=1)
    return time(hour=int(hour), minute=int(minute))


def utcnow() -> datetime:
    return datetime.now(get_app_timezone())
