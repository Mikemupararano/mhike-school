from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class AttendanceStatusCount(BaseModel):
    status: str
    count: int


class AttendanceClassSummary(BaseModel):
    class_group_id: int
    class_name: str | None = None
    total_records: int
    present: int
    late: int
    authorised_absence: int
    unauthorised_absence: int


class AttendanceRegisterSummary(BaseModel):
    session_id: int
    class_group_id: int
    class_name: str | None = None
    session_date: date
    session_type: str
    is_submitted: bool
    total_records: int


class AttendanceDashboardSummary(BaseModel):
    school_id: int
    summary_date: date
    total_records: int
    submitted_registers: int
    unsubmitted_registers: int
    present: int
    late: int
    authorised_absence: int
    unauthorised_absence: int
    registers: list[AttendanceRegisterSummary]
    classes: list[AttendanceClassSummary]
