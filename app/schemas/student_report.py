from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StudentReportBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    report_text: str = Field(min_length=1)
    grade: str | None = Field(default=None, max_length=50)

    work_covered: str | None = None
    teacher_notes: str | None = None
    generated_report_text: str | None = None

    academic_year: str = Field(min_length=1, max_length=20)
    term: str | None = Field(default=None, max_length=50)


class StudentReportCreate(StudentReportBase):
    student_id: int
    report_session_id: int | None = None


class StudentReportUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    report_text: str | None = Field(
        default=None,
        min_length=1,
    )
    grade: str | None = Field(
        default=None,
        max_length=50,
    )

    work_covered: str | None = None
    teacher_notes: str | None = None
    generated_report_text: str | None = None

    academic_year: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )
    term: str | None = Field(
        default=None,
        max_length=50,
    )
    teacher_id: int | None = None
    report_session_id: int | None = None


class StudentReportReviewDecision(BaseModel):
    review_comments: str | None = Field(
        default=None,
        max_length=5000,
    )


class StudentReportReviewDashboard(BaseModel):
    draft: int = 0
    submitted: int = 0
    approved: int = 0
    published: int = 0


class StudentReportRead(StudentReportBase):
    id: int
    school_id: int
    student_id: int
    teacher_id: int | None
    report_session_id: int | None

    status: str

    submitted_at: datetime | None
    submitted_by_id: int | None

    reviewed_at: datetime | None
    reviewed_by_id: int | None
    review_comments: str | None

    published: bool
    published_at: datetime | None
    published_by_id: int | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
