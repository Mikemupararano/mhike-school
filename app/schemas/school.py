from datetime import datetime

from pydantic import BaseModel


class SchoolOut(BaseModel):
    id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True
