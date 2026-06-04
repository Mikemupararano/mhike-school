from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StudentProgressSummary(BaseModel):
    student_id: int
    attendance_percentage: float
    assignments_completed: int
    average_assignment_score: float | None
    report_count: int
    latest_report_title: str | None
    recent_feedback_count: int

    model_config = ConfigDict(from_attributes=True)
