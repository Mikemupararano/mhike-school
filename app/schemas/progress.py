from pydantic import BaseModel
from datetime import datetime


class ProgressOut(BaseModel):
    id: int
    student_id: int
    lesson_id: int
    completed: bool
    last_seen_at: datetime

    class Config:
        from_attributes = True


class MarkLessonIn(BaseModel):
    completed: bool = True
