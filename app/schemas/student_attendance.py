from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class StudentAttendanceHistoryRecord(BaseModel):
    record_id: int
    attendance_session_id: int
    session_date: date
    session_type: str
    class_group_id: int
    class_name: str | None = None
    status: str
    notes: str | None = None
    marked_by_id: int | None = None
    created_at: datetime
    updated_at: datetime


class StudentAttendanceProfile(BaseModel):
    student_id: int
    student_name: str | None = None
    school_id: int
    total_records: int
    present: int
    late: int
    authorised_absence: int
    unauthorised_absence: int
    attendance_percentage: float
    history: list[StudentAttendanceHistoryRecord]
