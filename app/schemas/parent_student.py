from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ParentStudentBase(BaseModel):
    parent_id: int
    student_id: int


class ParentStudentCreate(ParentStudentBase):
    pass


class ParentStudentOut(ParentStudentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
