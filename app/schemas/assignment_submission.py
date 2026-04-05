from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AssignmentSubmissionBase(BaseModel):
    submission_text: Optional[str] = Field(default=None, max_length=10000)
    attachment_url: Optional[str] = Field(default=None, max_length=500)


class AssignmentSubmissionSubmit(AssignmentSubmissionBase):
    pass


class AssignmentSubmissionGrade(BaseModel):
    score: Optional[int] = Field(default=None, ge=0, le=1000)
    feedback: Optional[str] = Field(default=None, max_length=10000)
    status: str = Field(default="graded", max_length=50)


class AssignmentSubmissionOut(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    school_id: int
    submission_text: Optional[str]
    attachment_url: Optional[str]
    status: str
    score: Optional[int]
    feedback: Optional[str]
    graded_by: Optional[int]
    graded_at: Optional[datetime]
    submitted_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
