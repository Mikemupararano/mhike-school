from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ReportSessionBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    academic_year: str = Field(min_length=1, max_length=20)

    term: str | None = None
    active: bool = True

    include_work_covered: bool = True
    include_student_comment: bool = True

    include_exam_mark: bool = False
    include_attainment_grade: bool = False
    include_effort_grade: bool = False

    include_target_grade: bool = False
    include_next_steps: bool = False

    include_tutor_comment: bool = False


class ReportSessionCreate(ReportSessionBase):
    pass


class ReportSessionUpdate(BaseModel):
    title: str | None = None
    academic_year: str | None = None
    term: str | None = None

    active: bool | None = None

    include_work_covered: bool | None = None
    include_student_comment: bool | None = None

    include_exam_mark: bool | None = None
    include_attainment_grade: bool | None = None
    include_effort_grade: bool | None = None

    include_target_grade: bool | None = None
    include_next_steps: bool | None = None

    include_tutor_comment: bool | None = None


class ReportSessionRead(ReportSessionBase):
    id: int
    school_id: int
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }
