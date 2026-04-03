from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str
    school_id: Optional[int]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
