from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# =========================================================
# ENUMS
# =========================================================


class AttendanceSessionType(StrEnum):
    AM = "am"
    PM = "pm"


class AttendanceStatus(StrEnum):
    PRESENT = "present"
    LATE = "late"
    AUTHORISED_ABSENCE = "authorised_absence"
    UNAUTHORISED_ABSENCE = "unauthorised_absence"


class AbsenceRequestType(StrEnum):
    PLANNED = "planned"
    UNPLANNED = "unplanned"


class AbsenceRequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# =========================================================
# ATTENDANCE SESSION
# =========================================================


class AttendanceSessionBase(BaseModel):
    school_id: int
    class_group_id: int

    session_date: date
    session_type: AttendanceSessionType

    timetable_entry_id: Optional[int] = None
    timetable_period_id: Optional[int] = None


class AttendanceSessionCreate(AttendanceSessionBase):
    created_by_id: Optional[int] = None


class AttendanceSessionOut(AttendanceSessionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int

    is_submitted: bool
    submitted_at: Optional[datetime]
    submitted_by_id: Optional[int]

    created_by_id: Optional[int]

    created_at: datetime
    updated_at: datetime


# =========================================================
# ATTENDANCE RECORD
# =========================================================


class AttendanceRecordBase(BaseModel):
    attendance_session_id: int
    student_id: int

    status: AttendanceStatus

    notes: Optional[str] = Field(default=None, max_length=500)


class AttendanceRecordCreate(AttendanceRecordBase):
    marked_by_id: Optional[int] = None


class AttendanceRecordBulkCreate(BaseModel):
    records: list[AttendanceRecordCreate] = Field(
        ...,
        min_length=1,
        max_length=300,
    )


class AttendanceRecordUpdate(BaseModel):
    status: Optional[AttendanceStatus] = None
    notes: Optional[str] = Field(default=None, max_length=500)


class AttendanceRecordOut(AttendanceRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: int

    marked_by_id: Optional[int]

    created_at: datetime
    updated_at: datetime


# =========================================================
# ABSENCE REQUEST
# =========================================================


class AbsenceRequestBase(BaseModel):
    school_id: int
    student_id: int

    absence_type: AbsenceRequestType

    start_date: date
    end_date: date

    reason: str = Field(..., min_length=1)


class AbsenceRequestCreate(AbsenceRequestBase):
    submitted_by_id: Optional[int] = None


class AbsenceRequestReview(BaseModel):
    status: AbsenceRequestStatus

    review_note: Optional[str] = Field(default=None, max_length=500)


class AbsenceRequestOut(AbsenceRequestBase):
    model_config = ConfigDict(from_attributes=True)

    id: int

    submitted_by_id: Optional[int]
    reviewed_by_id: Optional[int]

    status: AbsenceRequestStatus

    review_note: Optional[str]

    created_at: datetime
    updated_at: datetime

    reviewed_at: Optional[datetime]


# =========================================================
# FILTERS
# =========================================================


class AttendanceFilter(BaseModel):
    school_id: Optional[int] = None

    class_group_id: Optional[int] = None
    student_id: Optional[int] = None

    session_date: Optional[date] = None

    session_type: Optional[AttendanceSessionType] = None
    status: Optional[AttendanceStatus] = None

    timetable_entry_id: Optional[int] = None
    timetable_period_id: Optional[int] = None

    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class AbsenceRequestFilter(BaseModel):
    school_id: Optional[int] = None

    student_id: Optional[int] = None

    absence_type: Optional[AbsenceRequestType] = None
    status: Optional[AbsenceRequestStatus] = None

    start_date_from: Optional[date] = None
    start_date_to: Optional[date] = None

    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
