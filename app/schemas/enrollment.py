from datetime import datetime

from pydantic import BaseModel


class EnrollmentCreate(BaseModel):
    user_id: int
    class_id: int


class EnrollmentOut(BaseModel):
    id: int
    user_id: int
    class_id: int
    created_at: datetime

    class Config:
        from_attributes = True
