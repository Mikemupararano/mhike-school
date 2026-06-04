from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ParentGradeOut(BaseModel):
    submission_id: int
    assignment_id: int
    student_id: int
    assignment_title: str
    max_score: int
    score: int | None
    feedback: str | None
    status: str
    submitted_at: datetime
    graded_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
