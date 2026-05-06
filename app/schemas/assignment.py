from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AssignmentBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    due_date: Optional[datetime] = None
    max_score: int = Field(default=100, ge=1, le=1000)
    is_published: bool = False


class AssignmentCreate(AssignmentBase):
    course_id: int = Field(gt=0)


class AssignmentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    due_date: Optional[datetime] = None
    max_score: Optional[int] = Field(default=None, ge=1, le=1000)
    is_published: Optional[bool] = None


class AssignmentPublishIn(BaseModel):
    is_published: bool = True


class AssignmentOut(AssignmentBase):
    id: int
    course_id: int
    school_id: int
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionCreate(BaseModel):
    submission_text: Optional[str] = None
    attachment_url: Optional[str] = None


class SubmissionGrade(BaseModel):
    score: int = Field(ge=0)
    feedback: Optional[str] = None


class SubmissionOut(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    submission_text: Optional[str] = None
    attachment_url: Optional[str] = None
    status: str
    score: Optional[int] = None
    feedback: Optional[str] = None
    graded_by: Optional[int] = None
    graded_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)