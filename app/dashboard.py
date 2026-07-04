from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_app_timezone
from app.db.models import (
    ExtractedFacts,
    HabitCategory,
    HabitPlan,
    Intervention,
    Log,
)
from app.habits.evidence import EffectiveEvidenceLedger, build_effective_evidence_ledger
from app.habits.plan import HabitPlanContext, get_habit_plan_context
from app.habits.state import (
    HabitReadState,
    HabitWeekState,
    get_dashboard_habit_rows,
    get_habit_week_states,
)

DashboardHabitStatus = Literal["done", "missing", "not_due", "unknown"]


class DashboardHabitDay(BaseModel):
    date: date
    weekday: str
    label: str
    status: DashboardHabitStatus
    is_corrected: bool = False
    is_checkin_answer: bool = False


class DashboardHabit(BaseModel):
    name: str
    category: str
    cadence_type: str
    cadence_value: Any = None
    cadence_summary: str
    success_condition: str
    today_status: DashboardHabitStatus
    is_corrected_today: bool = False
    week: list[DashboardHabitDay]
    weekly_done_count: int
    weekly_target_count: int


class DashboardLog(BaseModel):
    id: int
    text: str
    created_at: datetime
    logged_date: date | None = None
    effective_date: date | None = None
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
    plans = await _load_habit_plans(session, telegram_user_id)
    plan_contexts = list(plans)
    habit_states = {
        state.habit_name: state
        for state in await get_dashboard_habit_rows(
            session,
            telegram_user_id,
            plan_contexts,
            _dashboard_wall_time(current),
        )
    }
    week_states = {
        state.habit_name: state
        for state in await get_habit_week_states(
            session,
            telegram_user_id,
            plan_contexts,
            _dashboard_wall_time(current),
        )
    }
    recent_logs = await _load_recent_logs(session, telegram_user_id)
    recent_corrections = await build_effective_evidence_ledger(session, telegram_user_id)
    recent_interventions = await _load_recent_interventions(session, telegram_user_id)

    return DashboardData(
        habits=[
            _build_habit_row(plan, habit_states[plan.habit_name], week_states[plan.habit_name])
            for plan in plan_contexts
        ],
        recent_logs=_attach_corrections_to_logs(recent_logs, recent_corrections),
        recent_interventions=recent_interventions,
    )


async def _load_habit_plans(
    session: AsyncSession, telegram_user_id: int
) -> list[HabitPlanContext]:
    result = await session.execute(
        select(HabitPlan, HabitCategory.name)
        .join(HabitCategory, HabitCategory.id == HabitPlan.category_id)
        .where(HabitPlan.telegram_user_id == telegram_user_id)
        .order_by(HabitCategory.name, HabitPlan.habit_name)
    )
    rows: list[HabitPlanContext] = []
    for plan, category_name in result.all():
        rows.append(
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
        effective_date = log.logged_date or log.created_at.date()
        items.append(
            DashboardLog(
                id=log.id,
                text=log.text,
                created_at=log.created_at,
                logged_date=log.logged_date,
                effective_date=effective_date,
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
    state: HabitReadState,
    week: HabitWeekState,
) -> DashboardHabit:
    return DashboardHabit(
        name=plan.habit_name,
        category=plan.category_name,
        cadence_type=plan.cadence_type,
        cadence_value=plan.cadence_value,
        cadence_summary=_format_cadence(plan),
        success_condition=plan.success_condition,
        today_status=state.day_status,
        is_corrected_today=state.is_corrected,
        week=[
            DashboardHabitDay(
                date=day.date,
                weekday=day.weekday,
                label=day.label,
                status=day.status,
                is_corrected=day.is_corrected,
                is_checkin_answer=day.is_checkin_answer,
            )
            for day in week.days
        ],
        weekly_done_count=week.done_count,
        weekly_target_count=week.target_count,
    )


def _format_cadence(plan: HabitPlanContext) -> str:
    if plan.cadence_type == "daily":
        return "daily"
    if plan.cadence_type == "times_per_week":
        return f"{plan.cadence_value}x/week"
    if plan.cadence_type == "specific_weekdays":
        values = plan.cadence_value if isinstance(plan.cadence_value, list) else []
        return "/".join(str(day).title() for day in values) if values else "specific weekdays"
    return plan.cadence_type.replace("_", " ")


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


def utcnow() -> datetime:
    return datetime.now(get_app_timezone())


def _dashboard_wall_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.replace(tzinfo=None)
