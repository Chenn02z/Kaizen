from datetime import date, datetime

from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_app_timezone
from app.corrections.parser import parse_correction_intent
from app.corrections.schema import CorrectionIntent, CorrectionReference, OverrideStatus
from app.db.models import ExtractedFacts, HabitEvidenceOverride, Log
from app.gamification.xp import XPResult
from app.habits.evidence import get_effective_habit_state, recompute_progress_from_effective_state
from app.habits.plan import HabitPlanContext, get_habit_plan_context


class CorrectionOutcome(BaseModel):
    handled: bool
    applied: bool
    reply_text: str
    xp_result: XPResult | None = None


async def handle_correction_message(
    session: AsyncSession,
    *,
    telegram_user_id: int,
    text: str,
    now: datetime | None = None,
) -> CorrectionOutcome | None:
    plans = await get_habit_plan_context(session, telegram_user_id)
    intent = parse_correction_intent(text, plans)
    if intent is None:
        return None

    resolution = await _resolve_target(
        session, telegram_user_id, intent, plans, _app_datetime(now)
    )
    if resolution.follow_up is not None:
        return CorrectionOutcome(handled=True, applied=False, reply_text=resolution.follow_up)

    previous_state = await get_effective_habit_state(
        session,
        telegram_user_id,
        resolution.habit_name,
        resolution.target_date,
    )
    session.add(
        HabitEvidenceOverride(
            telegram_user_id=telegram_user_id,
            log_id=resolution.log_id,
            habit_name=resolution.habit_name,
            target_date=resolution.target_date,
            override_status=intent.override_status.value,
            user_text=text,
            reason=intent.reason,
        )
    )
    await session.flush()

    progress = await recompute_progress_from_effective_state(session, telegram_user_id)
    new_state = await get_effective_habit_state(
        session,
        telegram_user_id,
        resolution.habit_name,
        resolution.target_date,
    )

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
    return CorrectionOutcome(
        handled=True,
        applied=True,
        reply_text=_build_confirmation(
            resolution.habit_name,
            resolution.target_date,
            intent.override_status,
            previous_state.status if previous_state else None,
            new_state.status if new_state else None,
            progress.xp_delta,
        ),
        xp_result=result,
    )


class _Resolution(BaseModel):
    habit_name: str
    target_date: date
    log_id: int | None = None
    follow_up: str | None = None


async def _resolve_target(
    session: AsyncSession,
    telegram_user_id: int,
    intent: CorrectionIntent,
    plans: list[HabitPlanContext],
    now: datetime,
) -> _Resolution:
    recent = await _load_recent_log(session, telegram_user_id)
    habit_name = _resolve_habit_name(intent.habit_hint, plans, recent)
    if habit_name is None:
        if intent.habit_hint:
            options = ", ".join(plan.habit_name for plan in plans)
            return _Resolution(
                habit_name="",
                target_date=_app_date(now),
                follow_up=f"I couldn't match that habit. Say the habit name directly: {options}.",
            )
        return _Resolution(
            habit_name="",
            target_date=_app_date(now),
            follow_up=(
                "Which habit should I correct? "
                "Say something like 'count my last log as partial for gym'."
            ),
        )

    if intent.reference == CorrectionReference.today:
        return _Resolution(habit_name=habit_name, target_date=_app_date(now))

    if recent is None:
        return _Resolution(
            habit_name="",
            target_date=_app_date(now),
            follow_up=(
                "I couldn't find a recent log to correct yet. "
                "Send the log first, then correct it."
            ),
        )

    return _Resolution(
        habit_name=habit_name,
        target_date=_app_date(recent.created_at),
        log_id=recent.id,
    )


def _resolve_habit_name(
    habit_hint: str | None,
    plans: list[HabitPlanContext],
    recent: Log | None,
) -> str | None:
    if habit_hint:
        lowered = habit_hint.casefold()
        matches = [
            plan.habit_name
            for plan in plans
            if lowered == plan.habit_name.casefold()
            or lowered in {alias.casefold() for alias in plan.habit_aliases}
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            return None

    if recent is None:
        return None
    habits = getattr(recent, "_recent_habits", None)
    if isinstance(habits, list) and len(habits) == 1:
        return habits[0]
    return None


async def _load_recent_log(session: AsyncSession, telegram_user_id: int) -> Log | None:
    result = await session.execute(
        select(Log, ExtractedFacts)
        .join(ExtractedFacts, ExtractedFacts.log_id == Log.id, isouter=True)
        .where(Log.telegram_user_id == telegram_user_id)
        .order_by(desc(Log.created_at), desc(Log.id))
        .limit(1)
    )
    row = result.first()
    if row is None:
        return None
    log, facts = row
    setattr(log, "_recent_habits", list((facts.habits if facts else []) or []))
    return log


def _build_confirmation(
    habit_name: str,
    target_date: date,
    override_status: OverrideStatus,
    old_status: str | None,
    new_status: str | None,
    xp_delta: int,
) -> str:
    parts = [
        f"Got it. I updated {habit_name} for {target_date.isoformat()} "
        f"to {override_status.value}."
    ]
    if old_status != new_status:
        parts.append(
            f"Effective state changed from {old_status or 'none'} to {new_status or 'none'}."
        )
    if xp_delta > 0:
        parts.append(f"XP +{xp_delta}.")
    elif xp_delta < 0:
        parts.append(f"XP {xp_delta}.")
    return " ".join(parts)


def utcnow() -> datetime:
    return datetime.now(get_app_timezone())


def _app_datetime(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(get_app_timezone())
    if value.tzinfo is None:
        return value.replace(tzinfo=get_app_timezone())
    return value.astimezone(get_app_timezone())


def _app_date(value: datetime) -> date:
    return _app_datetime(value).date()
