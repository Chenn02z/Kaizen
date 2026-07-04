"""Tests for app.habits.cadence."""

from app.habits.cadence import HasCadence, format_cadence
from app.habits.commands import CadenceSpec
from app.habits.plan import HabitPlanContext


def _make_ctx(**overrides):
    defaults = dict(
        category_name="TEST",
        habit_name="test",
        direction="build",
        cadence_type="daily",
        cadence_value=None,
        success_condition="done",
        habit_aliases=[],
        known_triggers=[],
    )
    defaults.update(overrides)
    return HabitPlanContext(**defaults)


# ── HasCadence protocol ───────────────────────────────────────
def test_habit_plan_context_satisfies_protocol():
    ctx = _make_ctx()
    assert isinstance(ctx, HasCadence)


def test_cadence_spec_satisfies_protocol():
    spec = CadenceSpec(cadence_type="daily")
    assert isinstance(spec, HasCadence)


def test_dict_does_not_satisfy_protocol():
    assert not isinstance({"cadence_type": "daily"}, HasCadence)


# ── format_cadence ────────────────────────────────────────────
def test_format_none():
    assert format_cadence(None) == "unset"


def test_format_daily():
    assert format_cadence(CadenceSpec(cadence_type="daily")) == "daily"


def test_format_times_per_week():
    spec = CadenceSpec(cadence_type="times_per_week", cadence_value=3)
    assert format_cadence(spec) == "3x/week"


def test_format_specific_weekdays():
    spec = CadenceSpec(cadence_type="specific_weekdays", cadence_value=["mon", "wed", "fri"])
    result = format_cadence(spec)
    assert "Mon" in result and "Wed" in result and "Fri" in result
    assert "/" in result


def test_format_specific_weekdays_empty():
    spec = CadenceSpec(cadence_type="specific_weekdays", cadence_value=[])
    assert format_cadence(spec) == "specific weekdays"


def test_format_unknown_type_replace_underscores():
    ctx = _make_ctx(cadence_type="every_other_day")
    assert format_cadence(ctx) == "every other day"


def test_format_from_context():
    ctx = _make_ctx(cadence_type="times_per_week", cadence_value=5)
    assert format_cadence(ctx) == "5x/week"
