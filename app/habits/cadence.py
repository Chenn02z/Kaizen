"""Cadence formatting shared across callers."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class HasCadence(Protocol):
    """Structural interface satisfied by HabitPlanContext and CadenceSpec."""

    cadence_type: str
    cadence_value: Any


def format_cadence(source: HasCadence | None) -> str:
    """Render a cadence as a short human-readable string."""
    if source is None:
        return "unset"
    ct = source.cadence_type
    if ct == "daily":
        return "daily"
    if ct == "times_per_week":
        return f"{source.cadence_value}x/week"
    if ct == "specific_weekdays":
        values = source.cadence_value if isinstance(source.cadence_value, list) else []
        return "/".join(str(day).title() for day in values) if values else "specific weekdays"
    return ct.replace("_", " ")
