import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_app_timezone
from app.db.models import HabitEvidenceOverride, Intervention
from app.gamification.xp import XPResult
from app.habits.evidence import get_effective_habit_state, recompute_progress_from_effective_state
from app.habits.plan import HabitPlanContext, get_habit_plan_context

CHECKIN_ANSWER_REASON_PREFIX = "check-in answer"


class CheckInStatus(str, Enum):
    yes = "yes"
    partial = "partial"
    no = "no"


class ParsedCheckInAnswer(BaseModel):
    bare_status: CheckInStatus | None = None
    statuses: dict[str, CheckInStatus] = Field(default_factory=dict)


class CheckInOutcome(BaseModel):
    handled: bool
    applied: bool
    reply_text: str
    xp_result: XPResult | None = None


@dataclass(frozen=True)
class _OpenCheckIn:
    intervention: Intervention
    target_date: date
    target_habits: list[str]


async def handle_checkin_answer(
    session: AsyncSession,
    *,
    telegram_user_id: int,
    text: str,
    now: datetime | None = None,
) -> CheckInOutcome | None:
    current = _app_datetime(now)
    plans = await get_habit_plan_context(session, telegram_user_id)
    checkin = await _latest_same_day_checkin(session, telegram_user_id, plans, current)
    if checkin is None:
        return None

    parsed = parse_checkin_answer(text, checkin.target_habits, plans)
    if parsed is None:
        return None

    statuses = _resolve_statuses(parsed, checkin.target_habits)
    if statuses is None:
        return CheckInOutcome(
            handled=True,
            applied=False,
            reply_text=_build_multi_habit_follow_up(checkin.target_habits),
        )

    previous_states = {
        habit_name: await get_effective_habit_state(
            session,
            telegram_user_id,
            habit_name,
            checkin.target_date,
        )
        for habit_name in statuses
    }

    for habit_name, status in statuses.items():
        session.add(
            HabitEvidenceOverride(
                telegram_user_id=telegram_user_id,
                log_id=None,
                habit_name=habit_name,
                target_date=checkin.target_date,
                override_status=status.value,
                user_text=text,
                reason=f"{CHECKIN_ANSWER_REASON_PREFIX} for intervention {checkin.intervention.id}",
            )
        )
    checkin.intervention.engaged = True
    await session.flush()

    progress = await recompute_progress_from_effective_state(session, telegram_user_id)
    new_states = {
        habit_name: await get_effective_habit_state(
            session,
            telegram_user_id,
            habit_name,
            checkin.target_date,
        )
        for habit_name in statuses
    }

    result = (
        XPResult(
            xp_gained=progress.xp_delta,
            new_total_xp=progress.new_total_xp,
            old_level=progress.old_level,
            new_level=progress.new_level,
            levelled_up=progress.new_level > progress.old_level,
        )
        if progress.xp_delta != 0 or progress.new_level != progress.old_level
        else None
    )
    return CheckInOutcome(
        handled=True,
        applied=True,
        reply_text=_build_confirmation(
            statuses,
            checkin.target_date,
            {
                habit_name: previous_states[habit_name].status
                if previous_states[habit_name]
                else None
                for habit_name in statuses
            },
            {
                habit_name: new_states[habit_name].status if new_states[habit_name] else None
                for habit_name in statuses
            },
            progress.xp_delta,
        ),
        xp_result=result,
    )


def parse_checkin_answer(
    text: str,
    target_habits: list[str],
    plans: list[HabitPlanContext],
) -> ParsedCheckInAnswer | None:
    normalized = " ".join(text.strip().split())
    if not normalized:
        return None

    bare = _parse_status(normalized.strip(" .!?").casefold())
    if bare is not None:
        return ParsedCheckInAnswer(bare_status=bare)

    statuses: dict[str, CheckInStatus] = {}
    for segment in re.split(r"[,;\n]+", normalized):
        status_matches = re.findall(r"\b(yes|partial|no)\b", segment, flags=re.IGNORECASE)
        if len(status_matches) != 1:
            continue
        matched_habits = [
            habit_name
            for habit_name in target_habits
            if _segment_names_habit(segment, habit_name, plans)
        ]
        if len(matched_habits) != 1:
            continue
        statuses[matched_habits[0]] = CheckInStatus(status_matches[0].casefold())

    if statuses:
        return ParsedCheckInAnswer(statuses=statuses)
    return None


async def _latest_same_day_checkin(
    session: AsyncSession,
    telegram_user_id: int,
    plans: list[HabitPlanContext],
    now: datetime,
) -> _OpenCheckIn | None:
    target_date = now.date()
    result = await session.execute(
        select(Intervention)
        .where(Intervention.telegram_user_id == telegram_user_id)
        .where(Intervention.kind == "check-in")
        .where(Intervention.created_at >= _day_start(target_date))
        .where(Intervention.created_at < _day_start(target_date + timedelta(days=1)))
        .order_by(desc(Intervention.created_at), desc(Intervention.id))
    )
    for intervention in result.scalars().all():
        target_habits = _resolve_target_habits(intervention, plans)
        if target_habits:
            return _OpenCheckIn(
                intervention=intervention,
                target_date=target_date,
                target_habits=target_habits,
            )
    return None


def _resolve_target_habits(
    intervention: Intervention,
    plans: list[HabitPlanContext],
) -> list[str]:
    source = f"{intervention.reason} {intervention.message or ''}"
    return [
        plan.habit_name
        for plan in plans
        if _contains_term(source, plan.habit_name)
    ]


def _resolve_statuses(
    parsed: ParsedCheckInAnswer,
    target_habits: list[str],
) -> dict[str, CheckInStatus] | None:
    if parsed.bare_status is not None:
        if len(target_habits) != 1:
            return None
        return {target_habits[0]: parsed.bare_status}

    if set(parsed.statuses) == set(target_habits):
        return parsed.statuses
    return None


def _build_multi_habit_follow_up(target_habits: list[str]) -> str:
    examples = ", ".join(f"{habit} yes" for habit in target_habits)
    names = ", ".join(target_habits)
    return (
        f"Which habit should I update? Reply with each status, like '{examples}'. "
        f"I need one answer for: {names}."
    )


def _build_confirmation(
    statuses: dict[str, CheckInStatus],
    target_date: date,
    old_statuses: dict[str, str | None],
    new_statuses: dict[str, str | None],
    xp_delta: int,
) -> str:
    status_text = ", ".join(
        f"{habit_name}={status.value}" for habit_name, status in statuses.items()
    )
    parts = [f"Got it. I recorded {status_text} for {target_date.isoformat()}."]
    changed = [
        (
            f"{habit_name}: {old_statuses[habit_name] or 'none'} "
            f"-> {new_statuses[habit_name] or 'none'}"
        )
        for habit_name in statuses
        if old_statuses[habit_name] != new_statuses[habit_name]
    ]
    if changed:
        parts.append("Effective state changed: " + "; ".join(changed) + ".")
    if xp_delta > 0:
        parts.append(f"XP +{xp_delta}.")
    elif xp_delta < 0:
        parts.append(f"XP {xp_delta}.")
    return " ".join(parts)


def _segment_names_habit(
    segment: str,
    habit_name: str,
    plans: list[HabitPlanContext],
) -> bool:
    terms = [habit_name]
    plan = next((item for item in plans if item.habit_name == habit_name), None)
    if plan is not None:
        terms.extend(plan.habit_aliases)
    return any(_contains_term(segment, term) for term in terms)


def _contains_term(source: str, term: str) -> bool:
    if not term:
        return False
    return re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", source, re.IGNORECASE) is not None


def _parse_status(value: str) -> CheckInStatus | None:
    try:
        return CheckInStatus(value)
    except ValueError:
        return None


def _day_start(day: date) -> datetime:
    return datetime.combine(day, datetime.min.time(), tzinfo=get_app_timezone())


def _app_datetime(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(get_app_timezone())
    if value.tzinfo is None:
        return value.replace(tzinfo=get_app_timezone())
    return value.astimezone(get_app_timezone())
