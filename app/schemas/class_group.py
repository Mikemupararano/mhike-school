from datetime import datetime

from pydantic import BaseModel, Field


class ClassGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ClassGroupOut(BaseModel):
    id: int
    name: str
    school_id: int
    created_at: datetime

    class Config:
        from_attributes = True
