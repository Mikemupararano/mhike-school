from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ClassGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    teacher_id: Optional[int] = None


class ClassGroupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    teacher_id: Optional[int] = None


class ClassGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    school_id: int
    teacher_id: Optional[int] = None
    created_at: datetime
