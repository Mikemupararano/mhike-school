from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class AttendanceTrendPoint(BaseModel):
    trend_date: date
    total_records: int
    present: int
    late: int
    authorised_absence: int
    unauthorised_absence: int
    attendance_percentage: float


class AttendanceTrendSummary(BaseModel):
    school_id: int
    start_date: date
    end_date: date
    points: list[AttendanceTrendPoint]
