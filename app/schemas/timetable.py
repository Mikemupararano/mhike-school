from __future__ import annotations

from datetime import date, datetime, time
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TimetableDay(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class TimetableAssignmentType(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    CLASS_GROUP = "class_group"


# =========================================================
# TIMETABLE PERIODS
# =========================================================


class TimetablePeriodBase(BaseModel):
    school_id: int
    name: str = Field(..., max_length=100)
    short_name: str = Field(..., max_length=20)
    period_number: int
    start_time: time
    end_time: time

    is_registration: bool = False
    is_break: bool = False
    is_lunch: bool = False
    is_active: bool = True


class TimetablePeriodCreate(TimetablePeriodBase):
    pass


class TimetablePeriodUpdate(BaseModel):
    name: str | None = None
    short_name: str | None = None
    period_number: int | None = None
    start_time: time | None = None
    end_time: time | None = None

    is_registration: bool | None = None
    is_break: bool | None = None
    is_lunch: bool | None = None
    is_active: bool | None = None


class TimetablePeriodOut(TimetablePeriodBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# TIMETABLES
# =========================================================


class TimetableBase(BaseModel):
    school_id: int
    name: str = Field(..., max_length=150)
    academic_year: str = Field(..., max_length=20)

    effective_from: date
    effective_to: date | None = None

    is_active: bool = True


class TimetableCreate(TimetableBase):
    pass


class TimetableUpdate(BaseModel):
    name: str | None = None
    academic_year: str | None = None

    effective_from: date | None = None
    effective_to: date | None = None

    is_active: bool | None = None


class TimetableOut(TimetableBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# TIMETABLE ENTRIES
# =========================================================


class TimetableEntryBase(BaseModel):
    timetable_id: int
    school_id: int

    class_group_id: int | None = None
    course_id: int | None = None
    teacher_id: int | None = None

    timetable_period_id: int

    day_of_week: TimetableDay

    room: str | None = Field(default=None, max_length=100)
    title: str | None = Field(default=None, max_length=200)
    notes: str | None = None


class TimetableEntryCreate(TimetableEntryBase):
    pass


class TimetableEntryUpdate(BaseModel):
    class_group_id: int | None = None
    course_id: int | None = None
    teacher_id: int | None = None

    timetable_period_id: int | None = None

    day_of_week: TimetableDay | None = None

    room: str | None = None
    title: str | None = None
    notes: str | None = None


class TimetableEntryOut(TimetableEntryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# TIMETABLE ASSIGNMENTS
# =========================================================


class TimetableAssignmentBase(BaseModel):
    timetable_id: int
    school_id: int

    assignment_type: TimetableAssignmentType

    user_id: int | None = None
    class_group_id: int | None = None


class TimetableAssignmentCreate(TimetableAssignmentBase):
    pass


class TimetableAssignmentUpdate(BaseModel):
    user_id: int | None = None
    class_group_id: int | None = None


class TimetableAssignmentOut(TimetableAssignmentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# FILTERS
# =========================================================


class TimetableFilter(BaseModel):
    school_id: int | None = None
    academic_year: str | None = None
    is_active: bool | None = None

    limit: int = 50
    offset: int = 0


class TimetableEntryFilter(BaseModel):
    school_id: int | None = None

    timetable_id: int | None = None
    class_group_id: int | None = None
    course_id: int | None = None
    teacher_id: int | None = None

    day_of_week: TimetableDay | None = None

    limit: int = 50
    offset: int = 0


class TimetableAssignmentFilter(BaseModel):
    school_id: int | None = None

    timetable_id: int | None = None
    assignment_type: TimetableAssignmentType | None = None

    user_id: int | None = None
    class_group_id: int | None = None

    limit: int = 50
    offset: int = 0
