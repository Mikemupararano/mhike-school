from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


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
