from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class StudentReportBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    report_text: str = Field(min_length=1)
    grade: str | None = Field(default=None, max_length=50)
    academic_year: str = Field(min_length=1, max_length=20)
    term: str | None = Field(default=None, max_length=50)


class StudentReportCreate(StudentReportBase):
    student_id: int
    teacher_id: int | None = None


class StudentReportUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    report_text: str | None = Field(default=None, min_length=1)
    grade: str | None = Field(default=None, max_length=50)
    academic_year: str | None = Field(default=None, min_length=1, max_length=20)
    term: str | None = Field(default=None, max_length=50)
    teacher_id: int | None = None


class StudentReportRead(StudentReportBase):
    id: int
    school_id: int
    student_id: int
    teacher_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }
