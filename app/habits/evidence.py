from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_app_timezone
from app.corrections.schema import OverrideStatus
from app.db.models import (
    ExtractedFacts,
    HabitEvidenceOverride,
    HabitProgress,
    Log,
    UserProgress,
)
from app.gamification.xp import level_for_xp

_POSITIVE_STATUSES = {OverrideStatus.yes.value, OverrideStatus.partial.value}
_STATUS_XP = {
    OverrideStatus.yes.value: 50,
    OverrideStatus.partial.value: 20,
    OverrideStatus.no.value: 0,
    OverrideStatus.unmatched.value: 0,
}
_STATUS_PRIORITY = {
    OverrideStatus.unmatched.value: 0,
    OverrideStatus.no.value: 1,
    OverrideStatus.partial.value: 2,
    OverrideStatus.yes.value: 3,
}


@dataclass(frozen=True)
class EffectiveHabitState:
    habit_name: str
    target_date: date
    status: str
    corrected: bool
    log_id: int | None = None


@dataclass(frozen=True)
class EffectiveLogEvidence:
    log_id: int
    created_at: datetime
    text: str
    mood: str | None
    trigger: str | None
    context: str | None
    original_habits: list[str]
    original_adherence: str | None
    effective_habits: list[EffectiveHabitState]


@dataclass(frozen=True)
class EffectiveEvidenceLedger:
    logs: list[EffectiveLogEvidence]
    states_by_date: dict[date, dict[str, EffectiveHabitState]]


@dataclass(frozen=True)
class ProgressRecomputeResult:
    xp_delta: int
    old_total_xp: int
    new_total_xp: int
    old_level: int
    new_level: int


async def build_effective_evidence_ledger(
    session: AsyncSession,
    telegram_user_id: int,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> EffectiveEvidenceLedger:
    log_rows = await _load_log_rows(
        session,
        telegram_user_id,
        start_date=start_date,
        end_date=end_date,
    )
    overrides = await _load_latest_overrides(
        session,
        telegram_user_id,
        start_date=start_date,
        end_date=end_date,
    )

    states_by_date: dict[date, dict[str, EffectiveHabitState]] = {}
    logs: list[EffectiveLogEvidence] = []

    for log, facts in log_rows:
        target_date = _app_date(log.created_at)
        base_habits = list((facts.habits if facts else []) or [])
        candidate_habits = set(base_habits)
        candidate_habits.update(
            habit_name for day, habit_name in overrides.keys() if day == target_date
        )

        effective_habits: list[EffectiveHabitState] = []
        for habit_name in sorted(candidate_habits):
            status, corrected = _resolve_status(
                habit_name,
                target_date,
                base_habits,
                facts,
                overrides,
            )
            if status is None:
                continue
            state = EffectiveHabitState(
                habit_name=habit_name,
                target_date=target_date,
                status=status,
                corrected=corrected,
                log_id=log.id,
            )
            effective_habits.append(state)
            _merge_state(states_by_date, state)

        logs.append(
            EffectiveLogEvidence(
                log_id=log.id,
                created_at=log.created_at,
                text=log.text,
                mood=facts.mood if facts else None,
                trigger=facts.trigger if facts else None,
                context=facts.context if facts else None,
                original_habits=base_habits,
                original_adherence=facts.adherence if facts else None,
                effective_habits=effective_habits,
            )
        )

    for (target_day, habit_name), override in overrides.items():
        if start_date and target_day < start_date:
            continue
        if end_date and target_day > end_date:
            continue
        day_states = states_by_date.setdefault(target_day, {})
        if habit_name not in day_states:
            day_states[habit_name] = EffectiveHabitState(
                habit_name=habit_name,
                target_date=target_day,
                status=override.override_status,
                corrected=True,
                log_id=override.log_id,
            )

    return EffectiveEvidenceLedger(logs=logs, states_by_date=states_by_date)


async def get_effective_habit_state(
    session: AsyncSession,
    telegram_user_id: int,
    habit_name: str,
    target_date: date,
) -> EffectiveHabitState | None:
    ledger = await build_effective_evidence_ledger(
        session,
        telegram_user_id,
        start_date=target_date,
        end_date=target_date,
    )
    return ledger.states_by_date.get(target_date, {}).get(habit_name)


async def recompute_progress_from_effective_state(
    session: AsyncSession,
    telegram_user_id: int,
) -> ProgressRecomputeResult:
    ledger = await build_effective_evidence_ledger(session, telegram_user_id)

    total_xp = 0
    habit_xp: dict[str, int] = {}
    positive_days = {
        target_date
        for target_date, day_states in ledger.states_by_date.items()
        if any(state.status in _POSITIVE_STATUSES for state in day_states.values())
    }

    for target_day in sorted(ledger.states_by_date):
        day_states = ledger.states_by_date[target_day]
        day_xp = 0
        for state in day_states.values():
            xp = _STATUS_XP.get(state.status, 0)
            if xp <= 0:
                continue
            habit_xp[state.habit_name] = habit_xp.get(state.habit_name, 0) + xp
            day_xp += xp
        if day_xp > 0 and _has_three_day_streak(positive_days, target_day):
            day_xp += 10
        total_xp += day_xp

    old_user = (
        await session.execute(
            select(UserProgress).where(UserProgress.telegram_user_id == telegram_user_id)
        )
    ).scalar_one_or_none()
    old_total = old_user.xp if old_user else 0
    old_level = old_user.level if old_user else 1

    if old_user is None:
        old_user = UserProgress(telegram_user_id=telegram_user_id, xp=0, level=1)
        session.add(old_user)

    old_user.xp = total_xp
    old_user.level = level_for_xp(total_xp)

    existing_habits = (
        await session.execute(
            select(HabitProgress).where(HabitProgress.telegram_user_id == telegram_user_id)
        )
    ).scalars().all()
    existing_by_name = {row.habit_name: row for row in existing_habits}

    for habit_name, xp in habit_xp.items():
        row = existing_by_name.pop(habit_name, None)
        if row is None:
            row = HabitProgress(
                telegram_user_id=telegram_user_id,
                habit_name=habit_name,
                xp=0,
                level=1,
            )
            session.add(row)
        row.xp = xp
        row.level = level_for_xp(xp)

    for row in existing_by_name.values():
        row.xp = 0
        row.level = 1

    return ProgressRecomputeResult(
        xp_delta=total_xp - old_total,
        old_total_xp=old_total,
        new_total_xp=total_xp,
        old_level=old_level,
        new_level=level_for_xp(total_xp),
    )


def is_positive_status(status: str | None) -> bool:
    return status in _POSITIVE_STATUSES


def xp_for_status(status: str | None) -> int:
    if status is None:
        return 0
    return _STATUS_XP.get(status, 0)


def best_status(left: str | None, right: str | None) -> str | None:
    if left is None:
        return right
    if right is None:
        return left
    return left if _STATUS_PRIORITY[left] >= _STATUS_PRIORITY[right] else right


async def _load_log_rows(
    session: AsyncSession,
    telegram_user_id: int,
    *,
    start_date: date | None,
    end_date: date | None,
) -> list[tuple[Log, ExtractedFacts | None]]:
    stmt = (
        select(Log, ExtractedFacts)
        .join(ExtractedFacts, ExtractedFacts.log_id == Log.id, isouter=True)
        .where(Log.telegram_user_id == telegram_user_id)
        .order_by(Log.created_at, Log.id)
    )
    if start_date is not None:
        stmt = stmt.where(Log.created_at >= _day_start(start_date))
    if end_date is not None:
        stmt = stmt.where(Log.created_at < _day_start(end_date + timedelta(days=1)))
    result = await session.execute(stmt)
    return result.all()


async def _load_latest_overrides(
    session: AsyncSession,
    telegram_user_id: int,
    *,
    start_date: date | None,
    end_date: date | None,
) -> dict[tuple[date, str], HabitEvidenceOverride]:
    stmt = (
        select(HabitEvidenceOverride)
        .where(HabitEvidenceOverride.telegram_user_id == telegram_user_id)
        .order_by(
            HabitEvidenceOverride.target_date,
            HabitEvidenceOverride.habit_name,
            desc(HabitEvidenceOverride.created_at),
            desc(HabitEvidenceOverride.id),
        )
    )
    if start_date is not None:
        stmt = stmt.where(HabitEvidenceOverride.target_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(HabitEvidenceOverride.target_date <= end_date)
    result = await session.execute(stmt)

    latest: dict[tuple[date, str], HabitEvidenceOverride] = {}
    for row in result.scalars():
        key = (row.target_date, row.habit_name)
        latest.setdefault(key, row)
    return latest


def _resolve_status(
    habit_name: str,
    target_date: date,
    base_habits: list[str],
    facts: ExtractedFacts | None,
    overrides: dict[tuple[date, str], HabitEvidenceOverride],
) -> tuple[str | None, bool]:
    override = overrides.get((target_date, habit_name))
    if override is not None:
        return override.override_status, True
    if facts is None or habit_name not in base_habits:
        return None, False
    return facts.adherence, False


def _merge_state(
    states_by_date: dict[date, dict[str, EffectiveHabitState]],
    state: EffectiveHabitState,
) -> None:
    day_states = states_by_date.setdefault(state.target_date, {})
    existing = day_states.get(state.habit_name)
    if existing is None:
        day_states[state.habit_name] = state
        return
    chosen = best_status(existing.status, state.status)
    if chosen == existing.status:
        return
    day_states[state.habit_name] = state


def _has_three_day_streak(positive_days: set[date], target_day: date) -> bool:
    return all(target_day - timedelta(days=offset) in positive_days for offset in range(1, 4))


def _day_start(day: date) -> datetime:
    return datetime.combine(day, datetime.min.time(), tzinfo=get_app_timezone())


def _app_date(value: datetime) -> date:
    if value.tzinfo is None:
        return value.date()
    return value.astimezone(get_app_timezone()).date()
