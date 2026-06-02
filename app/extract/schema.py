from enum import Enum

from pydantic import BaseModel


class Adherence(str, Enum):
    yes = "yes"
    no = "no"
    partial = "partial"


class ExtractedFacts(BaseModel):
    habits: list[str]
    adherence: Adherence | None = None
    mood: str | None = None
    trigger: str | None = None
    context: str | None = None
