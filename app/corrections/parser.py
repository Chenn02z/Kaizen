import re
from collections.abc import Sequence

from app.corrections.schema import CorrectionIntent, CorrectionReference, OverrideStatus
from app.habits.plan import HabitPlanContext

_PATTERNS: tuple[tuple[re.Pattern[str], OverrideStatus, CorrectionReference, str], ...] = (
    (
        re.compile(r"^count that as (?P<habit>.+)$", re.IGNORECASE),
        OverrideStatus.yes,
        CorrectionReference.last_log,
        "user marked the last log as completed evidence",
    ),
    (
        re.compile(
            r"^count my last log as (?P<status>partial|done|yes) for (?P<habit>.+)$",
            re.IGNORECASE,
        ),
        OverrideStatus.yes,
        CorrectionReference.last_log,
        "user corrected the last log's adherence",
    ),
    (
        re.compile(r"^undo (?P<habit>.+) credit for today$", re.IGNORECASE),
        OverrideStatus.no,
        CorrectionReference.today,
        "user removed today's completion credit",
    ),
    (
        re.compile(r"^mark (?P<habit>.+) as missed$", re.IGNORECASE),
        OverrideStatus.no,
        CorrectionReference.today,
        "user marked the habit as missed",
    ),
    (
        re.compile(r"^that was not a[n]? (?P<habit>.+)$", re.IGNORECASE),
        OverrideStatus.no,
        CorrectionReference.last_log,
        "user said the last log should not count as this habit",
    ),
    (
        re.compile(r"^do not use that as evidence next time$", re.IGNORECASE),
        OverrideStatus.unmatched,
        CorrectionReference.last_log,
        "user said the last log should not be used as evidence",
    ),
)

_CORRECTION_STARTS = ("count ", "undo ", "mark ")
_CORRECTION_TERMS = ("evidence", "credit", "correction")


def parse_correction_intent(
    text: str,
    habit_plans: Sequence[HabitPlanContext],
) -> CorrectionIntent | None:
    normalized = " ".join(text.strip().split())
    if not normalized:
        return None

    for pattern, default_status, reference, reason in _PATTERNS:
        match = pattern.match(normalized)
        if not match:
            continue
        status = default_status
        if "status" in match.groupdict():
            status_value = match.group("status").casefold()
            status = OverrideStatus.partial if status_value == "partial" else OverrideStatus.yes
        habit_hint = match.groupdict().get("habit")
        return CorrectionIntent(
            override_status=status,
            reference=reference,
            habit_hint=_normalize_hint(habit_hint),
            reason=reason,
        )

    if _looks_like_correction(normalized, habit_plans):
        return CorrectionIntent(
            override_status=OverrideStatus.unmatched,
            reference=CorrectionReference.last_log,
            habit_hint=None,
            reason="correction-like message needs clarification",
        )
    return None


def _looks_like_correction(text: str, habit_plans: Sequence[HabitPlanContext]) -> bool:
    lower = text.casefold()
    if lower.startswith(_CORRECTION_STARTS):
        return True
    if any(term in lower for term in _CORRECTION_TERMS):
        return True
    known_terms = {
        item.casefold()
        for plan in habit_plans
        for item in [plan.habit_name, *plan.habit_aliases]
    }
    return any(term in lower for term in known_terms) and "use that as evidence" in lower


def _normalize_hint(value: str | None) -> str | None:
    if value is None:
        return None
    hint = value.strip().rstrip(".!?")
    return hint or None
