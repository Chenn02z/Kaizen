from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HabitProgress, UserProgress
from app.gamification.xp import xp_to_next_level


class HabitStats(BaseModel):
    name: str
    level: int
    xp: int


class UserStats(BaseModel):
    level: int
    xp: int
    xp_to_next_level: int
    habits: list[HabitStats]


async def get_user_stats(telegram_user_id: int, session: AsyncSession) -> UserStats:
    up = (
        await session.execute(
            select(UserProgress).where(UserProgress.telegram_user_id == telegram_user_id)
        )
    ).scalar_one_or_none()

    if up is None:
        return UserStats(level=1, xp=0, xp_to_next_level=100, habits=[])

    habits_result = await session.execute(
        select(HabitProgress).where(HabitProgress.telegram_user_id == telegram_user_id)
    )
    habits = [
        HabitStats(name=h.habit_name, level=h.level, xp=h.xp) for h in habits_result.scalars().all()
    ]
    return UserStats(
        level=up.level,
        xp=up.xp,
        xp_to_next_level=xp_to_next_level(up.xp),
        habits=habits,
    )
