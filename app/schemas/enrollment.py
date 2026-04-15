from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EnrollmentCreate(BaseModel):
    user_id: int
    class_id: int


class EnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    class_id: int
    created_at: datetime

    # Optional (safe for now, useful later)
    user_name: Optional[str] = None
    class_name: Optional[str] = None
