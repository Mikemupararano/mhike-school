from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportMemoryCreate(BaseModel):
    school_id: int

    teacher_id: int | None = None
    teacher_name: str | None = None

    subject: str
    year_group: str | None = None

    topics_studied: str | None = None
    teacher_notes: str | None = None

    generated_report: str | None = None
    final_report: str

    source_report_id: int | None = None


class ReportMemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int

    school_id: int

    teacher_id: int | None
    teacher_name: str | None

    subject: str
    year_group: str | None

    topics_studied: str | None
    teacher_notes: str | None

    generated_report: str | None
    final_report: str

    source_report_id: int | None

    approved: bool
    created_at: datetime
