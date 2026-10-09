"""Pydantic request models (input validation lives here)."""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class Status(str, Enum):
    accepted = "accepted"
    wrong_answer = "wrong_answer"
    time_limit = "time_limit"
    runtime_error = "runtime_error"


class ProblemIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    difficulty: Difficulty
    topic: str = Field(min_length=1, max_length=60)

    @field_validator("title", "topic")
    @classmethod
    def strip_and_check(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class SubmissionIn(BaseModel):
    problem_id: int = Field(gt=0)
    status: Status
    language: str = Field(min_length=1, max_length=30)
    runtime_ms: Optional[int] = Field(default=None, ge=0)
    # Optional so old attempts can be back-filled; defaults to "now" (UTC).
    submitted_at: Optional[datetime] = None
