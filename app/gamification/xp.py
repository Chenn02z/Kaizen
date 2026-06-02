import math
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ExtractedFacts as EFModel
from app.db.models import HabitProgress, Log, UserProgress
from app.extract.schema import Adherence, ExtractedFacts

_XP_PER_HABIT: dict[Adherence, int] = {
    Adherence.yes: 50,
    Adherence.partial: 20,
    Adherence.no: 0,
}


class XPResult(BaseModel):
    xp_gained: int
    new_total_xp: int
    old_level: int
    new_level: int
    levelled_up: bool


def level_for_xp(xp: int) -> int:
    return max(1, math.floor(math.sqrt(xp / 100)) + 1)


def xp_to_next_level(current_xp: int) -> int:
    return 100 * level_for_xp(current_xp) ** 2 - current_xp


async def _has_streak(session: AsyncSession, telegram_user_id: int) -> bool:
    """Return True if the user logged yes/partial adherence on each of the last 3 calendar days."""
    today = datetime.now(timezone.utc).date()
    days = [today - timedelta(days=i) for i in range(1, 4)]
    for day in days:
        result = await session.execute(
            select(EFModel)
            .join(Log, Log.id == EFModel.log_id)
            .where(Log.telegram_user_id == telegram_user_id)
            .where(
                Log.created_at
                >= datetime.combine(day, datetime.min.time()).replace(tzinfo=timezone.utc)
            )
            .where(
                Log.created_at
                < datetime.combine(day + timedelta(days=1), datetime.min.time()).replace(
                    tzinfo=timezone.utc
                )
            )
            .where(EFModel.adherence.in_(["yes", "partial"]))
        )
        if result.first() is None:
            return False
    return True


async def award_xp(facts: ExtractedFacts, telegram_user_id: int, session: AsyncSession) -> XPResult:
    habit_xp = _XP_PER_HABIT.get(facts.adherence, 0) if facts.adherence else 0
    base_xp = len(facts.habits) * habit_xp
    streak_bonus = 10 if base_xp > 0 and await _has_streak(session, telegram_user_id) else 0
    xp_gained = base_xp + streak_bonus

    # Upsert UserProgress
    result = await session.execute(
        select(UserProgress).where(UserProgress.telegram_user_id == telegram_user_id)
    )
    user_prog = result.scalar_one_or_none()
    if user_prog is None:
        user_prog = UserProgress(telegram_user_id=telegram_user_id, xp=0, level=1)
        session.add(user_prog)
        await session.flush()

    old_level = user_prog.level
    user_prog.xp += xp_gained
    new_level = level_for_xp(user_prog.xp)
    user_prog.level = new_level

    # Upsert HabitProgress for each habit
    for habit in facts.habits:
        h_result = await session.execute(
            select(HabitProgress)
            .where(HabitProgress.telegram_user_id == telegram_user_id)
            .where(HabitProgress.habit_name == habit)
        )
        habit_prog = h_result.scalar_one_or_none()
        if habit_prog is None:
            habit_prog = HabitProgress(
                telegram_user_id=telegram_user_id, habit_name=habit, xp=0, level=1
            )
            session.add(habit_prog)
            await session.flush()
        habit_prog.xp += habit_xp
        habit_prog.level = level_for_xp(habit_prog.xp)

    return XPResult(
        xp_gained=xp_gained,
        new_total_xp=user_prog.xp,
        old_level=old_level,
        new_level=new_level,
        levelled_up=new_level > old_level,
    )
