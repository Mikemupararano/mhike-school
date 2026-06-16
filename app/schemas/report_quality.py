from pydantic import BaseModel, Field


class ReportQualityCheckRequest(BaseModel):
    comment: str = Field(min_length=1)


class ReportQualityIssue(BaseModel):
    type: str
    message: str
    suggestion: str | None = None


class ReportQualityCheckResponse(BaseModel):
    original_comment: str
    corrected_comment: str
    issues: list[ReportQualityIssue]
