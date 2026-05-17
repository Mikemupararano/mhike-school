from __future__ import annotations

from pydantic import BaseModel


class PersistentAbsenteeSummary(BaseModel):
    student_id: int
    student_name: str | None = None
    class_group_id: int | None = None
    class_name: str | None = None
    total_records: int
    absence_count: int
    unauthorised_absence_count: int
    absence_percentage: float


class AttendanceAnalyticsSummary(BaseModel):
    school_id: int
    persistent_absence_threshold: float
    persistent_absentees: list[PersistentAbsenteeSummary]
