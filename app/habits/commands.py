from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    HabitCategory,
    HabitCommandFlow,
    HabitEvidenceOverride,
    HabitPlan,
    HabitProgress,
)
from app.habits.plan import ensure_default_habit_plan

DEFAULT_EVIDENCE_WINDOW = "20:00"

CadenceType = Literal["daily", "specific_weekdays", "times_per_week"]
FlowType = Literal["add", "edit"]

_YES = {"yes", "y"}
_NO = {"no", "n"}
_WEEKDAY_ALIASES = {
    "mon": "mon",
    "monday": "mon",
    "tue": "tue",
    "tues": "tue",
    "tuesday": "tue",
    "wed": "wed",
    "wednesday": "wed",
    "thu": "thu",
    "thur": "thu",
    "thurs": "thu",
    "thursday": "thu",
    "fri": "fri",
    "friday": "fri",
    "sat": "sat",
    "saturday": "sat",
    "sun": "sun",
    "sunday": "sun",
}
_WEEKDAY_ORDER = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


class CadenceSpec(BaseModel):
    cadence_type: CadenceType
    cadence_value: Any = None


class HabitAddDraft(BaseModel):
    name: str | None = None
    category_name: str | None = None
    category_is_new: bool = False
    pending_category_name: str | None = None
    cadence: CadenceSpec | None = None
    success_condition: str | None = None
    aliases: list[str] = []


class HabitEditDraft(BaseModel):
    target_habit_name: str | None = None
    name: str | None = None
    category_name: str | None = None
    category_is_new: bool = False
    cadence: CadenceSpec | None = None
    success_condition: str | None = None
    aliases: list[str] = []
    candidate_names: list[str] = []


class ExistingHabit(BaseModel):
    id: int
    category_id: int
    category_name: str
    habit_name: str
    cadence_type: str
    cadence_value: Any = None
    success_condition: str
    habit_aliases: list[str]


async def start_habit_add(
    session: AsyncSession,
    *,
    telegram_user_id: int,
    chat_id: int,
) -> str:
    await ensure_default_habit_plan(session, telegram_user_id)
    await _replace_flow(
        session,
        telegram_user_id=telegram_user_id,
        chat_id=chat_id,
        flow_type="add",
        step="add_name",
        data=HabitAddDraft().model_dump(),
    )
    return "Habit name?"


async def start_habit_edit(
    session: AsyncSession,
    *,
    telegram_user_id: int,
    chat_id: int,
    target_text: str,
) -> str:
    await ensure_default_habit_plan(session, telegram_user_id)
    target = _clean_text(target_text)
    if not target:
        await _replace_flow(
            session,
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            flow_type="edit",
            step="edit_target",
            data=HabitEditDraft().model_dump(),
        )
        return "Which habit should I edit? Send the exact habit name."

    resolution = await _resolve_habit(session, telegram_user_id, target)
    if resolution.match is None and not resolution.candidates:
        return f"I could not find a habit matching '{target}'. Send /habits to review the plan."
    if resolution.match is None:
        draft = HabitEditDraft(
            candidate_names=[habit.habit_name for habit in resolution.candidates]
        )
        await _replace_flow(
            session,
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            flow_type="edit",
            step="edit_target",
            data=draft.model_dump(),
        )
        names = ", ".join(draft.candidate_names)
        return f"I found multiple matching habits: {names}. Send one exact habit name."

    await _replace_flow(
        session,
        telegram_user_id=telegram_user_id,
        chat_id=chat_id,
        flow_type="edit",
        step="edit_fields",
        data=_draft_from_existing_habit(resolution.match).model_dump(),
    )
    return _render_edit_prompt(resolution.match.habit_name)


async def handle_habit_flow_message(
    session: AsyncSession,
    *,
    telegram_user_id: int,
    chat_id: int,
    text: str,
) -> str | None:
    flow = await _get_flow(session, telegram_user_id)
    if flow is None:
        return None

    normalized = _normalize_response(text)
    if normalized == "cancel":
        await _clear_flow(session, telegram_user_id)
        return "Canceled. No habit-plan changes were saved."

    flow.chat_id = chat_id
    if flow.flow_type == "add":
        return await _handle_add_flow(session, flow, text)
    if flow.flow_type == "edit":
        return await _handle_edit_flow(session, flow, text)

    await _clear_flow(session, telegram_user_id)
    return (
        "I cleared an unsupported habit command flow. "
        "Send /habit_add or /habit_edit to start again."
    )


async def _handle_add_flow(
    session: AsyncSession,
    flow: HabitCommandFlow,
    text: str,
) -> str:
    draft = HabitAddDraft.model_validate(flow.data)
    value = _clean_text(text)

    if flow.step == "add_name":
        name = _normalize_habit_name(value)
        if not name:
            return "Habit name cannot be empty. Send the habit name."
        if await _habit_name_exists(session, flow.telegram_user_id, name):
            return f"'{name}' already exists. Send a different habit name."
        draft.name = name
        _set_flow(flow, step="add_category", data=draft.model_dump())
        return "Category? Choose an existing category or type a new one."

    if flow.step == "add_category":
        category_name = _normalize_category_name(value)
        if not category_name:
            return "Category cannot be empty. Send an existing category or a new category name."
        existing = await _find_category_name(session, flow.telegram_user_id, category_name)
        if existing is not None:
            draft.category_name = existing
            draft.category_is_new = False
            draft.pending_category_name = None
            _set_flow(flow, step="add_cadence", data=draft.model_dump())
            return "Cadence? Send daily, weekdays, specific weekdays like mon/wed/fri, or 3x/week."
        draft.pending_category_name = category_name
        _set_flow(flow, step="add_confirm_category", data=draft.model_dump())
        return f"Create new category '{category_name}'? yes/no"

    if flow.step == "add_confirm_category":
        response = _normalize_response(text)
        if response in _YES and draft.pending_category_name:
            draft.category_name = draft.pending_category_name
            draft.category_is_new = True
            draft.pending_category_name = None
            _set_flow(flow, step="add_cadence", data=draft.model_dump())
            return "Cadence? Send daily, weekdays, specific weekdays like mon/wed/fri, or 3x/week."
        if response in _NO:
            draft.pending_category_name = None
            _set_flow(flow, step="add_category", data=draft.model_dump())
            return "Category? Choose an existing category or type a new one."
        return f"Create new category '{draft.pending_category_name}'? yes/no"

    if flow.step == "add_cadence":
        cadence = _parse_cadence(value)
        if cadence is None:
            return (
                "I only support daily, weekdays, specific weekdays like mon/wed/fri, "
                "or N times per week like 3x/week."
            )
        draft.cadence = cadence
        _set_flow(flow, step="add_success", data=draft.model_dump())
        return "What counts as success?"

    if flow.step == "add_success":
        if not value:
            return "Success condition cannot be empty. What counts as success?"
        draft.success_condition = value
        _set_flow(flow, step="add_aliases", data=draft.model_dump())
        return 'Aliases/examples? Send comma-separated examples or "skip".'

    if flow.step == "add_aliases":
        draft.aliases = [] if _normalize_response(text) == "skip" else _parse_aliases(value)
        _set_flow(flow, step="add_confirm", data=draft.model_dump())
        return _render_add_summary(draft)

    if flow.step == "add_confirm":
        response = _normalize_response(text)
        if response in _YES:
            await _create_habit_from_draft(session, flow.telegram_user_id, draft)
            await _clear_flow(session, flow.telegram_user_id)
            return f"Saved habit '{draft.name}'."
        if response in _NO:
            await _clear_flow(session, flow.telegram_user_id)
            return "No habit was created. Send /habit_add to start again."
        return "Confirm this habit? yes/no"

    await _clear_flow(session, flow.telegram_user_id)
    return "I cleared an unsupported habit add step. Send /habit_add to start again."


async def _handle_edit_flow(
    session: AsyncSession,
    flow: HabitCommandFlow,
    text: str,
) -> str:
    draft = HabitEditDraft.model_validate(flow.data)
    value = _clean_text(text)

    if flow.step == "edit_target":
        resolution = await _resolve_habit(session, flow.telegram_user_id, value)
        if resolution.match is None:
            if resolution.candidates:
                names = ", ".join(habit.habit_name for habit in resolution.candidates)
                return f"I found multiple matching habits: {names}. Send one exact habit name."
            return "I could not find that habit. Send an exact habit name, or cancel."
        _set_flow(
            flow,
            step="edit_fields",
            data=_draft_from_existing_habit(resolution.match).model_dump(),
        )
        return _render_edit_prompt(resolution.match.habit_name)

    if flow.step == "edit_fields":
        response = _normalize_response(text)
        if response in _YES:
            await _save_edit_draft(session, flow.telegram_user_id, draft)
            await _clear_flow(session, flow.telegram_user_id)
            return f"Saved updates for '{draft.name}'."
        if response in _NO:
            await _clear_flow(session, flow.telegram_user_id)
            return "No habit changes were saved."

        error = await _apply_edit_update(session, flow.telegram_user_id, draft, value)
        if error is not None:
            return error
        _set_flow(flow, step="edit_fields", data=draft.model_dump())
        return _render_edit_summary(draft)

    await _clear_flow(session, flow.telegram_user_id)
    return "I cleared an unsupported habit edit step. Send /habit_edit <habit> to start again."


async def _apply_edit_update(
    session: AsyncSession,
    telegram_user_id: int,
    draft: HabitEditDraft,
    text: str,
) -> str | None:
    if ":" not in text:
        return (
            "Send one field as 'name: ...', 'category: ...', 'cadence: ...', "
            "'success: ...', or 'aliases: ...'."
        )
    field, raw_value = text.split(":", maxsplit=1)
    field = field.strip().casefold()
    value = _clean_text(raw_value)

    if field == "name":
        name = _normalize_habit_name(value)
        if not name:
            return "Habit name cannot be empty."
        if await _habit_name_exists(
            session,
            telegram_user_id,
            name,
            excluding=draft.target_habit_name,
        ):
            return f"'{name}' already exists. Send a different habit name."
        draft.name = name
        return None

    if field == "category":
        category_name = _normalize_category_name(value)
        if not category_name:
            return "Category cannot be empty."
        existing = await _find_category_name(session, telegram_user_id, category_name)
        draft.category_name = existing or category_name
        draft.category_is_new = existing is None
        return None

    if field == "cadence":
        cadence = _parse_cadence(value)
        if cadence is None:
            return (
                "I only support daily, weekdays, specific weekdays like mon/wed/fri, "
                "or N times per week like 3x/week."
            )
        draft.cadence = cadence
        return None

    if field in {"success", "success condition"}:
        if not value:
            return "Success condition cannot be empty."
        draft.success_condition = value
        return None

    if field in {"alias", "aliases", "examples"}:
        draft.aliases = [] if _normalize_response(value) == "skip" else _parse_aliases(value)
        return None

    return (
        "I can edit name, category, cadence, success, or aliases. "
        "Send one field like 'aliases: gym, lifted'."
    )


async def _create_habit_from_draft(
    session: AsyncSession,
    telegram_user_id: int,
    draft: HabitAddDraft,
) -> None:
    if (
        draft.name is None
        or draft.category_name is None
        or draft.cadence is None
        or draft.success_condition is None
    ):
        raise ValueError("habit add draft is incomplete")
    category = await _get_or_create_category(session, telegram_user_id, draft.category_name)
    session.add(
        HabitPlan(
            telegram_user_id=telegram_user_id,
            category_id=category.id,
            habit_name=draft.name,
            direction="build",
            cadence_type=draft.cadence.cadence_type,
            cadence_value=draft.cadence.cadence_value,
            success_condition=draft.success_condition,
            habit_aliases=draft.aliases,
            known_triggers=[],
            goal=None,
            fallback_checkin_enabled=True,
            expected_evidence_window=DEFAULT_EVIDENCE_WINDOW,
        )
    )
    await session.flush()


async def _save_edit_draft(
    session: AsyncSession,
    telegram_user_id: int,
    draft: HabitEditDraft,
) -> None:
    if (
        draft.target_habit_name is None
        or draft.name is None
        or draft.category_name is None
        or draft.cadence is None
        or draft.success_condition is None
    ):
        raise ValueError("habit edit draft is incomplete")

    category = await _get_or_create_category(session, telegram_user_id, draft.category_name)
    result = await session.execute(
        select(HabitPlan)
        .where(HabitPlan.telegram_user_id == telegram_user_id)
        .where(HabitPlan.habit_name == draft.target_habit_name)
    )
    plan = result.scalar_one()
    old_name = plan.habit_name
    plan.category_id = category.id
    plan.habit_name = draft.name
    plan.cadence_type = draft.cadence.cadence_type
    plan.cadence_value = draft.cadence.cadence_value
    plan.success_condition = draft.success_condition
    plan.habit_aliases = draft.aliases

    if old_name != draft.name:
        await session.execute(
            update(HabitProgress)
            .where(HabitProgress.telegram_user_id == telegram_user_id)
            .where(HabitProgress.habit_name == old_name)
            .values(habit_name=draft.name)
        )
        await session.execute(
            update(HabitEvidenceOverride)
            .where(HabitEvidenceOverride.telegram_user_id == telegram_user_id)
            .where(HabitEvidenceOverride.habit_name == old_name)
            .values(habit_name=draft.name)
        )
    await session.flush()


async def _get_or_create_category(
    session: AsyncSession, telegram_user_id: int, category_name: str
) -> HabitCategory:
    result = await session.execute(
        select(HabitCategory)
        .where(HabitCategory.telegram_user_id == telegram_user_id)
        .where(HabitCategory.name == category_name)
    )
    category = result.scalar_one_or_none()
    if category is not None:
        return category
    category = HabitCategory(telegram_user_id=telegram_user_id, name=category_name)
    session.add(category)
    await session.flush()
    return category


class HabitResolution(BaseModel):
    match: ExistingHabit | None = None
    candidates: list[ExistingHabit] = []


async def _resolve_habit(
    session: AsyncSession, telegram_user_id: int, target: str
) -> HabitResolution:
    habits = await _load_existing_habits(session, telegram_user_id)
    normalized = _normalize_habit_name(target)
    exact = [habit for habit in habits if habit.habit_name.casefold() == normalized]
    if len(exact) == 1:
        return HabitResolution(match=exact[0])
    if len(exact) > 1:
        return HabitResolution(candidates=exact)

    alias_matches = [
        habit
        for habit in habits
        if any(alias.casefold() == normalized for alias in habit.habit_aliases)
    ]
    if len(alias_matches) == 1:
        return HabitResolution(match=alias_matches[0])
    if len(alias_matches) > 1:
        return HabitResolution(candidates=alias_matches)
    return HabitResolution()


async def _load_existing_habits(
    session: AsyncSession, telegram_user_id: int
) -> list[ExistingHabit]:
    result = await session.execute(
        select(HabitPlan, HabitCategory.name)
        .join(HabitCategory, HabitCategory.id == HabitPlan.category_id)
        .where(HabitPlan.telegram_user_id == telegram_user_id)
        .order_by(HabitPlan.habit_name)
    )
    return [
        ExistingHabit(
            id=plan.id,
            category_id=plan.category_id,
            category_name=category_name,
            habit_name=plan.habit_name,
            cadence_type=plan.cadence_type,
            cadence_value=plan.cadence_value,
            success_condition=plan.success_condition,
            habit_aliases=plan.habit_aliases or [],
        )
        for plan, category_name in result.all()
    ]


def _draft_from_existing_habit(habit: ExistingHabit) -> HabitEditDraft:
    return HabitEditDraft(
        target_habit_name=habit.habit_name,
        name=habit.habit_name,
        category_name=habit.category_name,
        category_is_new=False,
        cadence=CadenceSpec(
            cadence_type=habit.cadence_type,  # type: ignore[arg-type]
            cadence_value=habit.cadence_value,
        ),
        success_condition=habit.success_condition,
        aliases=habit.habit_aliases,
    )


async def _habit_name_exists(
    session: AsyncSession,
    telegram_user_id: int,
    habit_name: str,
    *,
    excluding: str | None = None,
) -> bool:
    result = await session.execute(
        select(HabitPlan.habit_name).where(HabitPlan.telegram_user_id == telegram_user_id)
    )
    for existing_name in result.scalars().all():
        if excluding is not None and existing_name == excluding:
            continue
        if existing_name.casefold() == habit_name.casefold():
            return True
    return False


async def _find_category_name(
    session: AsyncSession, telegram_user_id: int, category_name: str
) -> str | None:
    result = await session.execute(
        select(HabitCategory.name).where(HabitCategory.telegram_user_id == telegram_user_id)
    )
    for existing_name in result.scalars().all():
        if existing_name.casefold() == category_name.casefold():
            return existing_name
    return None


async def _get_flow(session: AsyncSession, telegram_user_id: int) -> HabitCommandFlow | None:
    result = await session.execute(
        select(HabitCommandFlow).where(HabitCommandFlow.telegram_user_id == telegram_user_id)
    )
    return result.scalar_one_or_none()


async def _replace_flow(
    session: AsyncSession,
    *,
    telegram_user_id: int,
    chat_id: int,
    flow_type: FlowType,
    step: str,
    data: dict[str, Any],
) -> None:
    flow = await _get_flow(session, telegram_user_id)
    if flow is None:
        session.add(
            HabitCommandFlow(
                telegram_user_id=telegram_user_id,
                chat_id=chat_id,
                flow_type=flow_type,
                step=step,
                data=data,
            )
        )
    else:
        flow.chat_id = chat_id
        flow.flow_type = flow_type
        flow.step = step
        flow.data = data
    await session.flush()


async def _clear_flow(session: AsyncSession, telegram_user_id: int) -> None:
    await session.execute(
        delete(HabitCommandFlow).where(HabitCommandFlow.telegram_user_id == telegram_user_id)
    )
    await session.flush()


def _set_flow(flow: HabitCommandFlow, *, step: str, data: dict[str, Any]) -> None:
    flow.step = step
    flow.data = data


def _parse_cadence(value: str) -> CadenceSpec | None:
    normalized = _normalize_response(value)
    if normalized == "daily":
        return CadenceSpec(cadence_type="daily", cadence_value=None)
    if normalized == "weekdays":
        return CadenceSpec(
            cadence_type="specific_weekdays",
            cadence_value=["mon", "tue", "wed", "thu", "fri"],
        )
    if normalized in {"weekends", "weekend"}:
        return CadenceSpec(cadence_type="specific_weekdays", cadence_value=["sat", "sun"])

    weekdays = _parse_weekdays(normalized)
    if weekdays:
        return CadenceSpec(cadence_type="specific_weekdays", cadence_value=weekdays)

    weekly_count = _parse_weekly_count(normalized)
    if weekly_count is not None and weekly_count > 0:
        return CadenceSpec(cadence_type="times_per_week", cadence_value=weekly_count)
    return None


def _parse_weekdays(value: str) -> list[str]:
    tokens = [
        token
        for token in value.replace(",", " ").replace("/", " ").replace("-", " ").split()
        if token
    ]
    if not tokens:
        return []
    matched = [_WEEKDAY_ALIASES[token] for token in tokens if token in _WEEKDAY_ALIASES]
    if len(matched) != len(tokens):
        return []
    return [day for day in _WEEKDAY_ORDER if day in set(matched)]


def _parse_weekly_count(value: str) -> int | None:
    if "week" not in value:
        return None
    digits = "".join(char if char.isdigit() else " " for char in value).split()
    if len(digits) != 1:
        return None
    count = int(digits[0])
    return count if 1 <= count <= 7 else None


def _parse_aliases(value: str) -> list[str]:
    aliases: list[str] = []
    seen: set[str] = set()
    for item in value.split(","):
        alias = _clean_text(item).casefold()
        if not alias or alias in seen:
            continue
        aliases.append(alias)
        seen.add(alias)
    return aliases


def _render_add_summary(draft: HabitAddDraft) -> str:
    aliases = ", ".join(draft.aliases) if draft.aliases else "none"
    category_note = " (new)" if draft.category_is_new else ""
    return (
        "Confirm this habit? yes/no\n"
        f"- name: {draft.name}\n"
        f"- category: {draft.category_name}{category_note}\n"
        f"- cadence: {_format_cadence(draft.cadence)}\n"
        f"- success: {draft.success_condition}\n"
        f"- aliases: {aliases}"
    )


def _render_edit_prompt(habit_name: str) -> str:
    return (
        f"Editing '{habit_name}'. Send one field update at a time:\n"
        "- name: new name\n"
        "- category: category name\n"
        "- cadence: daily, weekdays, mon/wed/fri, or 3x/week\n"
        "- success: what counts as success\n"
        "- aliases: comma-separated examples\n"
        "Send yes to save, no to discard, or cancel."
    )


def _render_edit_summary(draft: HabitEditDraft) -> str:
    aliases = ", ".join(draft.aliases) if draft.aliases else "none"
    category_note = " (new)" if draft.category_is_new else ""
    return (
        "Updated draft. Save it? yes/no, or send another field update.\n"
        f"- name: {draft.name}\n"
        f"- category: {draft.category_name}{category_note}\n"
        f"- cadence: {_format_cadence(draft.cadence)}\n"
        f"- success: {draft.success_condition}\n"
        f"- aliases: {aliases}"
    )


def _format_cadence(cadence: CadenceSpec | None) -> str:
    if cadence is None:
        return "unset"
    if cadence.cadence_type == "daily":
        return "daily"
    if cadence.cadence_type == "times_per_week":
        return f"{cadence.cadence_value}x/week"
    if cadence.cadence_type == "specific_weekdays":
        values = cadence.cadence_value if isinstance(cadence.cadence_value, list) else []
        return ", ".join(str(day) for day in values)
    return cadence.cadence_type


def _clean_text(value: str) -> str:
    return " ".join(value.strip().split())


def _normalize_response(value: str) -> str:
    return _clean_text(value).casefold()


def _normalize_habit_name(value: str) -> str:
    return _clean_text(value).casefold()


def _normalize_category_name(value: str) -> str:
    return _clean_text(value).upper()
