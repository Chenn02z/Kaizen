"""Typed proactive intervention policy decisions."""

import logging
from collections.abc import Awaitable, Callable
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.habits.plan import DueHabit, build_fallback_checkin_message

logger = logging.getLogger(__name__)

PolicyAction = Literal["send_check_in", "send_nudge", "stay_silent"]
DecisionSource = Literal["daily_cap", "fallback_checkin", "llm", "llm_error"]
AgentDecisionAction = Literal["respond", "silent"]


class InterventionPolicyContext(BaseModel):
    telegram_user_id: int
    local_date: date
    day_start: datetime
    day_end: datetime
    proactive_count_today: int
    daily_cap: int
    due_habits_missing_evidence: list[DueHabit] = Field(default_factory=list)
    has_fallback_checkin_today: bool = False
    habit_state_summary: str = ""


class AgentInterventionDecision(BaseModel):
    action: AgentDecisionAction
    reason: str = "agent decision"
    message: str | None = None
    technique: str | None = None

    @classmethod
    def from_agent_state(cls, state: dict) -> "AgentInterventionDecision":
        return cls(
            action=state.get("decision", "silent"),
            reason=(
                state.get("decision_reason")
                or state.get("silence_reason")
                or "agent decision"
            ),
            message=state.get("reply_text"),
            technique=state.get("technique"),
        )


class InterventionDecision(BaseModel):
    action: PolicyAction
    source: DecisionSource
    reason: str
    message: str | None = None
    technique: str | None = None
    due_habits: list[str] = Field(default_factory=list)

    @property
    def intervention_kind(self) -> Literal["check-in", "proactive", "silence"]:
        if self.action == "send_check_in":
            return "check-in"
        if self.action == "send_nudge":
            return "proactive"
        return "silence"

    @property
    def should_send(self) -> bool:
        return self.action in {"send_check_in", "send_nudge"} and self.message is not None


ProactiveDecisionAdapter = Callable[
    [InterventionPolicyContext],
    Awaitable[AgentInterventionDecision],
]


class InterventionPolicy:
    async def decide(
        self,
        context: InterventionPolicyContext,
        llm_decider: ProactiveDecisionAdapter,
    ) -> InterventionDecision:
        if context.proactive_count_today >= context.daily_cap:
            return InterventionDecision(
                action="stay_silent",
                source="daily_cap",
                reason="daily cap reached",
            )

        due_habits = context.due_habits_missing_evidence
        if due_habits and not context.has_fallback_checkin_today:
            habit_names = [habit.habit_name for habit in due_habits]
            return InterventionDecision(
                action="send_check_in",
                source="fallback_checkin",
                reason="fallback check-in: missing evidence for " + ", ".join(habit_names),
                message=build_fallback_checkin_message(due_habits),
                due_habits=habit_names,
            )

        try:
            agent_decision = await llm_decider(context)
        except Exception:
            logger.exception(
                "intervention policy: LLM decision adapter failed for user %s",
                context.telegram_user_id,
            )
            return InterventionDecision(
                action="stay_silent",
                source="llm_error",
                reason="graph error",
            )

        if agent_decision.action == "respond" and agent_decision.message:
            return InterventionDecision(
                action="send_nudge",
                source="llm",
                reason=agent_decision.reason,
                message=agent_decision.message,
                technique=agent_decision.technique,
            )

        if agent_decision.action == "respond":
            return InterventionDecision(
                action="stay_silent",
                source="llm",
                reason=agent_decision.reason or "agent response missing message",
            )

        return InterventionDecision(
            action="stay_silent",
            source="llm",
            reason=agent_decision.reason,
        )
