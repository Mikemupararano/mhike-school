from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProgressOut(BaseModel):
    id: int
    student_id: int
    lesson_id: int
    completed: bool
    last_seen_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarkLessonIn(BaseModel):
    completed: bool = True
