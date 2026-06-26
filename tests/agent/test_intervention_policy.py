from datetime import date, datetime, timezone

from app.agent.intervention_policy import (
    AgentInterventionDecision,
    InterventionPolicy,
    InterventionPolicyContext,
)
from app.habits.plan import DueHabit


def _context(**overrides) -> InterventionPolicyContext:
    values = {
        "telegram_user_id": 12345,
        "local_date": date(2026, 6, 24),
        "day_start": datetime(2026, 6, 24, tzinfo=timezone.utc),
        "day_end": datetime(2026, 6, 25, tzinfo=timezone.utc),
        "proactive_count_today": 0,
        "daily_cap": 4,
        "due_habits_missing_evidence": [],
        "has_fallback_checkin_today": False,
        "habit_state_summary": "- gym: missing",
    }
    values.update(overrides)
    return InterventionPolicyContext(**values)


def _due_habit(name: str = "gym") -> DueHabit:
    return DueHabit(
        habit_name=name,
        category_name="FITNESS",
        success_condition="Completed a gym workout session",
        reason="habit has no completion evidence today",
    )


async def test_policy_daily_cap_stays_silent_without_llm_adapter() -> None:
    called = False

    async def decider(context: InterventionPolicyContext) -> AgentInterventionDecision:
        nonlocal called
        called = True
        return AgentInterventionDecision(action="respond", reason="should not run")

    decision = await InterventionPolicy().decide(
        _context(proactive_count_today=4),
        decider,
    )

    assert decision.action == "stay_silent"
    assert decision.source == "daily_cap"
    assert decision.reason == "daily cap reached"
    assert decision.intervention_kind == "silence"
    assert not called


async def test_policy_missing_due_habit_sends_checkin_without_llm_adapter() -> None:
    called = False

    async def decider(context: InterventionPolicyContext) -> AgentInterventionDecision:
        nonlocal called
        called = True
        return AgentInterventionDecision(action="respond", reason="should not run")

    decision = await InterventionPolicy().decide(
        _context(due_habits_missing_evidence=[_due_habit()]),
        decider,
    )

    assert decision.action == "send_check_in"
    assert decision.source == "fallback_checkin"
    assert decision.intervention_kind == "check-in"
    assert decision.reason == "fallback check-in: missing evidence for gym"
    assert (
        decision.message
        == "Quick check-in: did you complete gym today? Reply yes, partial, or no."
    )
    assert decision.due_habits == ["gym"]
    assert not called


async def test_policy_existing_checkin_prevents_second_checkin_without_langgraph() -> None:
    called_with_summary = ""

    async def decider(context: InterventionPolicyContext) -> AgentInterventionDecision:
        nonlocal called_with_summary
        called_with_summary = context.habit_state_summary
        return AgentInterventionDecision(
            action="silent",
            reason="already asked for a check-in",
        )

    decision = await InterventionPolicy().decide(
        _context(
            due_habits_missing_evidence=[_due_habit("read")],
            has_fallback_checkin_today=True,
            habit_state_summary="- read: missing",
        ),
        decider,
    )

    assert decision.action == "stay_silent"
    assert decision.source == "llm"
    assert decision.reason == "already asked for a check-in"
    assert called_with_summary == "- read: missing"


async def test_policy_graph_error_records_silence_without_langgraph() -> None:
    async def decider(context: InterventionPolicyContext) -> AgentInterventionDecision:
        raise RuntimeError("boom")

    decision = await InterventionPolicy().decide(_context(), decider)

    assert decision.action == "stay_silent"
    assert decision.source == "llm_error"
    assert decision.reason == "graph error"
    assert decision.intervention_kind == "silence"


async def test_policy_llm_response_becomes_recordable_nudge() -> None:
    async def decider(context: InterventionPolicyContext) -> AgentInterventionDecision:
        return AgentInterventionDecision(
            action="respond",
            reason="recent gym drift",
            technique="implementation intentions",
            message="Use implementation intentions: choose the gym trigger before work ends.",
        )

    decision = await InterventionPolicy().decide(_context(), decider)

    assert decision.action == "send_nudge"
    assert decision.source == "llm"
    assert decision.intervention_kind == "proactive"
    assert decision.reason == "recent gym drift"
    assert decision.technique == "implementation intentions"
    assert decision.should_send
