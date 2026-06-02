"""Tests for gamification XP logic — one test per acceptance criterion."""

from unittest.mock import AsyncMock, patch

import pytest  # noqa: F401 — used by pytest.mark.asyncio

from app.db.models import UserProgress
from app.extract.schema import Adherence, ExtractedFacts
from app.gamification.stats import UserStats
from app.gamification.xp import award_xp, level_for_xp

# ---------------------------------------------------------------------------
# AC1: XP per adherence type (pure-function + DB-backed)
# ---------------------------------------------------------------------------


def test_level_for_xp_boundaries() -> None:
    assert level_for_xp(0) == 1
    assert level_for_xp(99) == 1
    assert level_for_xp(100) == 2
    assert level_for_xp(399) == 2
    assert level_for_xp(400) == 3


@pytest.mark.asyncio
async def test_xp_award_yes(db_session) -> None:
    """yes adherence with 2 habits awards 100 XP (no streak)."""
    facts = ExtractedFacts(habits=["running", "meditation"], adherence=Adherence.yes)
    with patch("app.gamification.xp._has_streak", new=AsyncMock(return_value=False)):
        result = await award_xp(facts, telegram_user_id=1, session=db_session)
    await db_session.commit()

    assert result.xp_gained == 100
    assert result.new_total_xp == 100


@pytest.mark.asyncio
async def test_xp_award_partial(db_session) -> None:
    """partial adherence with 1 habit awards 20 XP."""
    facts = ExtractedFacts(habits=["running"], adherence=Adherence.partial)
    with patch("app.gamification.xp._has_streak", new=AsyncMock(return_value=False)):
        result = await award_xp(facts, telegram_user_id=2, session=db_session)
    await db_session.commit()

    assert result.xp_gained == 20


@pytest.mark.asyncio
async def test_xp_award_no(db_session) -> None:
    """no adherence awards 0 XP."""
    facts = ExtractedFacts(habits=["running"], adherence=Adherence.no)
    with patch("app.gamification.xp._has_streak", new=AsyncMock(return_value=False)):
        result = await award_xp(facts, telegram_user_id=3, session=db_session)
    await db_session.commit()

    assert result.xp_gained == 0


# ---------------------------------------------------------------------------
# AC2: Level-up at correct threshold — test 1→2 and 2→3 boundaries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_level_up_1_to_2(db_session) -> None:
    """Starting at 80 XP, +50 XP crosses the level 1→2 boundary at 100 XP."""
    user_prog = UserProgress(telegram_user_id=11, xp=80, level=1)
    db_session.add(user_prog)
    await db_session.flush()

    facts = ExtractedFacts(habits=["running"], adherence=Adherence.yes)
    with patch("app.gamification.xp._has_streak", new=AsyncMock(return_value=False)):
        result = await award_xp(facts, telegram_user_id=11, session=db_session)
    await db_session.commit()

    assert result.levelled_up is True
    assert result.new_level == 2


@pytest.mark.asyncio
async def test_level_up_boundary(db_session) -> None:
    """Starting at 380 XP, +50 XP (yes, 1 habit) crosses into level 3."""
    # Seed the user at 380 XP, level 2
    user_prog = UserProgress(telegram_user_id=10, xp=380, level=2)
    db_session.add(user_prog)
    await db_session.flush()

    facts = ExtractedFacts(habits=["running"], adherence=Adherence.yes)
    with patch("app.gamification.xp._has_streak", new=AsyncMock(return_value=False)):
        result = await award_xp(facts, telegram_user_id=10, session=db_session)
    await db_session.commit()

    assert result.xp_gained == 50
    assert result.new_total_xp == 430
    assert result.levelled_up is True
    assert result.new_level == 3


# ---------------------------------------------------------------------------
# AC3: Streak bonus
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_streak_bonus(db_session) -> None:
    """Streak bonus of 10 XP fires when last 3 days all have yes/partial."""
    facts = ExtractedFacts(habits=["running"], adherence=Adherence.yes)
    with patch("app.gamification.xp._has_streak", new=AsyncMock(return_value=True)):
        result = await award_xp(facts, telegram_user_id=4, session=db_session)
    await db_session.commit()

    # 50 XP (yes, 1 habit) + 10 streak bonus = 60
    assert result.xp_gained == 60


# ---------------------------------------------------------------------------
# AC4: GET /me returns valid UserStats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_me_endpoint(client, db_session) -> None:
    """GET /me returns valid UserStats JSON after awarding XP."""
    from app.config import settings

    facts = ExtractedFacts(habits=["yoga"], adherence=Adherence.yes)
    with patch("app.gamification.xp._has_streak", new=AsyncMock(return_value=False)):
        await award_xp(facts, telegram_user_id=settings.allowed_user_id, session=db_session)
    await db_session.commit()

    response = await client.get("/me")
    assert response.status_code == 200
    data = response.json()
    # Validate it parses as UserStats
    stats = UserStats.model_validate(data)
    assert stats.xp == 50
    assert len(stats.habits) == 1
    assert stats.habits[0].name == "yoga"


# ---------------------------------------------------------------------------
# AC5: GET /miniapp returns 200 with SDK script tag
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_miniapp_contains_sdk(client) -> None:
    response = await client.get("/miniapp")
    assert response.status_code == 200
    assert "telegram-web-app.js" in response.text
