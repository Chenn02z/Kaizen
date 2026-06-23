from enum import Enum

from pydantic import BaseModel


class OverrideStatus(str, Enum):
    yes = "yes"
    partial = "partial"
    no = "no"
    unmatched = "unmatched"


class CorrectionReference(str, Enum):
    last_log = "last_log"
    today = "today"


class CorrectionIntent(BaseModel):
    override_status: OverrideStatus
    reference: CorrectionReference
    habit_hint: str | None = None
    reason: str
