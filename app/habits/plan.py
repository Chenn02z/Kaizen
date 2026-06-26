from datetime import date, datetime, timedelta
from typing import Any, Sequence

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_app_timezone
from app.db.models import HabitCategory, HabitPlan, Intervention
from app.habits.state import get_due_habits

_DEFAULT_WINDOW = "20:00"


class HabitPlanContext(BaseModel):
    category_name: str
    habit_name: str
    direction: str
    cadence_type: str
    cadence_value: Any = None
    success_condition: str
    habit_aliases: list[str]
    known_triggers: list[str]
    goal: str | None = None
    fallback_checkin_enabled: bool = True
    expected_evidence_window: str | None = None


class DueHabit(BaseModel):
    habit_name: str
    category_name: str
    success_condition: str
    reason: str


_SEED_HABITS: tuple[dict[str, Any], ...] = (
    {
        "category_name": "FITNESS",
        "habit_name": "run",
        "direction": "build",
        "cadence_type": "times_per_week",
        "cadence_value": 3,
        "success_condition": "Completed a real run session",
        "habit_aliases": ["ran", "went for a run", "5k", "jogged"],
        "known_triggers": [],
        "goal": None,
    },
    {
        "category_name": "FITNESS",
        "habit_name": "gym",
        "direction": "build",
        "cadence_type": "times_per_week",
        "cadence_value": 3,
        "success_condition": "Completed a gym workout session",
        "habit_aliases": ["gym", "lifted", "workout", "trained chest"],
        "known_triggers": [],
        "goal": None,
    },
    {
        "category_name": "CAREER",
        "habit_name": "leetcode",
        "direction": "build",
        "cadence_type": "daily",
        "cadence_value": None,
        "success_condition": "Solved or seriously attempted at least one Leetcode session",
        "habit_aliases": ["leetcode", "did one problem", "solved two mediums", "practiced DSA"],
        "known_triggers": [],
        "goal": None,
    },
    {
        "category_name": "CAREER",
        "habit_name": "personal project",
        "direction": "build",
        "cadence_type": "times_per_week",
        "cadence_value": 3,
        "success_condition": "Made meaningful progress on a personal project",
        "habit_aliases": [
            "started a new project",
            "built a feature",
            "shipped a fix",
            "worked on the app",
        ],
        "known_triggers": [],
        "goal": None,
    },
    {
        "category_name": "SELF",
        "habit_name": "read",
        "direction": "build",
        "cadence_type": "daily",
        "cadence_value": None,
        "success_condition": "Completed a real reading session",
        "habit_aliases": ["read 20 pages", "finished a chapter", "kept reading", "read before bed"],
        "known_triggers": [],
        "goal": None,
    },
)


async def ensure_default_habit_plan(session: AsyncSession, telegram_user_id: int) -> None:
    result = await session.execute(
        select(HabitPlan.id).where(HabitPlan.telegram_user_id == telegram_user_id).limit(1)
    )
    if result.scalar_one_or_none() is not None:
        return

    categories: dict[str, HabitCategory] = {}
    for item in _SEED_HABITS:
        category_name = item["category_name"]
        category = categories.get(category_name)
        if category is None:
            category = HabitCategory(telegram_user_id=telegram_user_id, name=category_name)
            session.add(category)
            categories[category_name] = category
    await session.flush()

    for item in _SEED_HABITS:
        session.add(
            HabitPlan(
                telegram_user_id=telegram_user_id,
                category_id=categories[item["category_name"]].id,
                habit_name=item["habit_name"],
                direction=item["direction"],
                cadence_type=item["cadence_type"],
                cadence_value=item["cadence_value"],
                success_condition=item["success_condition"],
                habit_aliases=item["habit_aliases"],
                known_triggers=item["known_triggers"],
                goal=item["goal"],
                fallback_checkin_enabled=True,
                expected_evidence_window=_DEFAULT_WINDOW,
            )
        )
    await session.flush()


async def get_habit_plan_context(
    session: AsyncSession, telegram_user_id: int
) -> list[HabitPlanContext]:
    await ensure_default_habit_plan(session, telegram_user_id)
    result = await session.execute(
        select(HabitPlan, HabitCategory.name)
        .join(HabitCategory, HabitCategory.id == HabitPlan.category_id)
        .where(HabitPlan.telegram_user_id == telegram_user_id)
        .order_by(HabitCategory.name, HabitPlan.habit_name)
    )
    return [
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
        for plan, category_name in result.all()
    ]


def render_habit_plan_for_prompt(plans: Sequence[HabitPlanContext]) -> str:
    if not plans:
        return "No habit plan is available."
    lines = []
    for plan in plans:
        aliases = ", ".join(plan.habit_aliases) if plan.habit_aliases else "none"
        cadence = (
            plan.cadence_type
            if plan.cadence_value is None
            else f"{plan.cadence_type}={plan.cadence_value}"
        )
        lines.append(
            "- "
            f"{plan.habit_name} ({plan.category_name}, {plan.direction}, {cadence}): "
            f"{plan.success_condition}. Aliases/examples: {aliases}."
        )
    return "\n".join(lines)


async def due_habits_missing_evidence(
    session: AsyncSession,
    telegram_user_id: int,
    now: datetime | None = None,
) -> list[DueHabit]:
    current = _app_datetime(now)
    plans = await get_habit_plan_context(session, telegram_user_id)
    due_states = await get_due_habits(session, telegram_user_id, plans, current)
    return [
        DueHabit(
            habit_name=state.habit_name,
            category_name=state.category_name,
            success_condition=state.success_condition,
            reason=state.due_reason or "habit has no completion evidence today",
        )
        for state in due_states
    ]


async def has_fallback_checkin_today(
    session: AsyncSession,
    telegram_user_id: int,
    today: date | None = None,
) -> bool:
    target = today or datetime.now(get_app_timezone()).date()
    result = await session.execute(
        select(Intervention.id)
        .where(Intervention.telegram_user_id == telegram_user_id)
        .where(Intervention.kind == "check-in")
        .where(Intervention.created_at >= _day_start(target))
        .where(Intervention.created_at < _day_start(target + timedelta(days=1)))
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


def build_fallback_checkin_message(due_habits: Sequence[DueHabit]) -> str:
    names = [habit.habit_name for habit in due_habits]
    if len(names) == 1:
        habit_text = names[0]
    else:
        habit_text = ", ".join(names[:-1]) + f", and {names[-1]}"
    return f"Quick check-in: did you complete {habit_text} today? Reply yes, partial, or no."


def _day_start(day: date) -> datetime:
    return datetime.combine(day, datetime.min.time(), tzinfo=get_app_timezone())


def _app_datetime(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(get_app_timezone())
    if value.tzinfo is None:
        return value.replace(tzinfo=get_app_timezone())
    return value.astimezone(get_app_timezone())
