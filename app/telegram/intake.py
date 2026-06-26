import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.runner import run_user_message
from app.checkins.service import handle_checkin_answer
from app.corrections.service import handle_correction_message
from app.db.models import ExtractedFacts as ExtractedFactsModel
from app.db.models import Log
from app.db.session import AsyncSessionLocal
from app.extract.extractor import extract
from app.extract.schema import ExtractedFacts
from app.gamification.xp import XPResult
from app.habits.evidence import recompute_progress_from_effective_state
from app.habits.plan import HabitPlanContext, get_habit_plan_context
from app.memory.store import store_facts
from app.rag.replies import answer_reflection, is_reflection_query
from app.telegram.webapp import dashboard_inline_keyboard

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TelegramIntakeMessage:
    telegram_user_id: int
    chat_id: int
    text: str = ""


@dataclass(frozen=True)
class TelegramReply:
    chat_id: int
    text: str
    reply_markup: dict[str, Any] | None = None


@dataclass(frozen=True)
class IntakeOutcome:
    replies: tuple[TelegramReply, ...] = field(default_factory=tuple)
    handled: bool = False

    @classmethod
    def skip(cls) -> "IntakeOutcome":
        return cls(handled=True)

    @classmethod
    def reply(
        cls,
        *,
        chat_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> "IntakeOutcome":
        return cls(
            replies=(TelegramReply(chat_id=chat_id, text=text, reply_markup=reply_markup),),
            handled=True,
        )


async def handle_message(message: TelegramIntakeMessage) -> IntakeOutcome:
    """Route one allowed Telegram message.

    Routing order is intentionally centralized here:
    dashboard commands, habit-plan commands, check-in answers, corrections,
    unsupported slash commands, and finally ordinary logs.
    """
    command = _parse_command(message.text)
    if command in {"/start", "/dashboard", "/app"}:
        return _dashboard_reply(message.chat_id)

    if command in {"/habits", "/habit_add", "/habit_edit"}:
        async with AsyncSessionLocal() as session:
            return await _handle_habit_command(session, message, command)

    async with AsyncSessionLocal() as session:
        checkin_answer = await handle_checkin_answer(
            session,
            telegram_user_id=message.telegram_user_id,
            text=message.text,
        )
        if checkin_answer is not None and checkin_answer.handled:
            await session.commit()
            return IntakeOutcome.reply(chat_id=message.chat_id, text=checkin_answer.reply_text)

        correction = await handle_correction_message(
            session,
            telegram_user_id=message.telegram_user_id,
            text=message.text,
        )
        if correction is not None and correction.handled:
            await session.commit()
            return IntakeOutcome.reply(chat_id=message.chat_id, text=correction.reply_text)

    if command is not None:
        return IntakeOutcome.reply(
            chat_id=message.chat_id,
            text=(
                f"I don't support {command} yet. Supported commands: "
                "/start, /dashboard, /app, /habits, /habit_add, /habit_edit."
            ),
        )

    return await _handle_log_message(message)


def _dashboard_reply(chat_id: int) -> IntakeOutcome:
    reply_markup = dashboard_inline_keyboard()
    if reply_markup is None:
        return IntakeOutcome.reply(
            chat_id=chat_id,
            text="Kaizen dashboard is not configured yet. Set PUBLIC_URL to your HTTPS deployment.",
        )
    return IntakeOutcome.reply(
        chat_id=chat_id,
        text="Open your dashboard:",
        reply_markup=reply_markup,
    )


async def _handle_habit_command(
    session: AsyncSession,
    message: TelegramIntakeMessage,
    command: str,
) -> IntakeOutcome:
    if command == "/habits":
        plans = await get_habit_plan_context(session, message.telegram_user_id)
        await session.commit()
        return IntakeOutcome.reply(
            chat_id=message.chat_id,
            text=_render_habit_plan_summary(plans),
        )

    await session.rollback()
    if command == "/habit_add":
        return IntakeOutcome.reply(
            chat_id=message.chat_id,
            text=(
                "Habit add is reserved for the structured onboarding flow. "
                "Use /habits to review the current plan for now."
            ),
        )

    return IntakeOutcome.reply(
        chat_id=message.chat_id,
        text=(
            "Habit edit is reserved for the structured onboarding flow. "
            "Send /habit_edit <habit> once that flow is enabled."
        ),
    )


async def _handle_log_message(message: TelegramIntakeMessage) -> IntakeOutcome:
    facts: ExtractedFacts | None = None
    xp_result: XPResult | None = None
    async with AsyncSessionLocal() as session:
        log = Log(telegram_user_id=message.telegram_user_id, text=message.text)
        session.add(log)
        await session.flush()

        try:
            habit_plans = await get_habit_plan_context(session, message.telegram_user_id)
            facts = await extract(message.text, habit_plans)
            session.add(
                ExtractedFactsModel(
                    log_id=log.id,
                    habits=facts.habits,
                    adherence=facts.adherence.value if facts.adherence else None,
                    mood=facts.mood,
                    trigger=facts.trigger,
                    context=facts.context,
                )
            )
            await session.flush()
            progress = await recompute_progress_from_effective_state(
                session, message.telegram_user_id
            )
            if progress.xp_delta != 0 or progress.new_level != progress.old_level:
                xp_result = XPResult(
                    xp_gained=progress.xp_delta,
                    new_total_xp=progress.new_total_xp,
                    old_level=progress.old_level,
                    new_level=progress.new_level,
                    levelled_up=progress.new_level > progress.old_level,
                )
            await asyncio.get_running_loop().run_in_executor(
                None, store_facts, facts, message.text, message.telegram_user_id
            )
        except Exception:
            logger.exception("extraction failed for log_id=%s", log.id)

        await session.commit()

    reply_text = message.text
    try:
        if is_reflection_query(message.text):
            reply_text = await answer_reflection(message.text, message.telegram_user_id)
        else:
            reply_text = await run_user_message(
                telegram_user_id=message.telegram_user_id,
                user_text=message.text,
                facts=facts,
            )
    except Exception:
        logger.exception("reply generation failed")

    if xp_result and xp_result.xp_gained > 0:
        reply_text += f"\n\n+{xp_result.xp_gained} XP · Level {xp_result.new_level} \U0001f5e1️"
        if xp_result.levelled_up:
            reply_text += f"\n⬆️ LEVEL UP — you are now Level {xp_result.new_level}!"

    return IntakeOutcome.reply(chat_id=message.chat_id, text=reply_text)


def _parse_command(text: Optional[str]) -> str | None:
    if not text:
        return None
    first = text.strip().split(maxsplit=1)[0]
    if not first.startswith("/"):
        return None
    return first.split("@", maxsplit=1)[0].casefold()


def _render_habit_plan_summary(plans: list[HabitPlanContext]) -> str:
    if not plans:
        return "No habit plan is available yet."

    grouped: dict[str, list[HabitPlanContext]] = defaultdict(list)
    for plan in plans:
        grouped[plan.category_name].append(plan)

    sections: list[str] = []
    for category_name in sorted(grouped):
        lines = [category_name.upper()]
        for plan in sorted(grouped[category_name], key=lambda item: item.habit_name):
            lines.append(
                f"- {plan.habit_name}: {_format_cadence(plan)} - {plan.success_condition}"
            )
            aliases = ", ".join(plan.habit_aliases) if plan.habit_aliases else "none"
            lines.append(f"  aliases: {aliases}")
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def _format_cadence(plan: HabitPlanContext) -> str:
    if plan.cadence_type == "daily":
        return "daily"
    if plan.cadence_type == "times_per_week":
        return f"{plan.cadence_value}x/week"
    if plan.cadence_type == "specific_weekdays":
        values = plan.cadence_value if isinstance(plan.cadence_value, list) else []
        return ", ".join(str(day) for day in values) if values else "specific weekdays"
    return plan.cadence_type
