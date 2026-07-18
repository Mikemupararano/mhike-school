from __future__ import annotations

from pydantic import BaseModel, Field


class ReportQualityCheckRequest(BaseModel):
    comment: str = Field(
        min_length=1,
        description="The report comment to check and improve.",
    )


class ReportQualityIssue(BaseModel):
    type: str
    message: str
    suggestion: str | None = None


class ReportQualityCheckResponse(BaseModel):
    original_comment: str
    corrected_comment: str
    issues: list[ReportQualityIssue]


# ---------------------------------------------------------------------------
# Generate report from teacher notes
# ---------------------------------------------------------------------------


class ReportNotesGenerateRequest(BaseModel):
    notes: str = Field(
        min_length=1,
        description="Teacher notes or bullet points.",
    )
    student_name: str | None = None
    subject: str | None = None
    year_group: str | None = None


class ReportNotesGenerateResponse(BaseModel):
    notes: str
    generated_comment: str
