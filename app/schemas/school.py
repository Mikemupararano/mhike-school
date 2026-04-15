from datetime import datetime
from pydantic import BaseModel, Field


# =========================
# Create schema
# =========================
class SchoolCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


# =========================
# Response schema
# =========================
class SchoolOut(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}
