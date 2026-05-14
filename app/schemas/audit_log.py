from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class AuditLogBase(BaseModel):
    action: str = Field(..., min_length=1)
    entity_type: str = Field(..., min_length=1)
    entity_id: Optional[int] = None

    target_user_id: Optional[int] = None
    school_id: Optional[int] = None

    metadata: Optional[Dict[str, Any]] = None


class AuditLogCreate(AuditLogBase):
    actor_id: Optional[int] = None
    actor_school_id: Optional[int] = None


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int

    actor_id: Optional[int] = None
    actor_school_id: Optional[int] = None
    actor_email: Optional[str] = None

    action: str
    entity_type: str
    entity_id: Optional[int] = None

    target_user_id: Optional[int] = None
    target_user_email: Optional[str] = None

    school_id: Optional[int] = None
    school_name: Optional[str] = None

    metadata: Optional[Dict[str, Any]] = None

    created_at: datetime


class AuditLogFilter(BaseModel):
    actor_id: Optional[int] = None
    actor_email: Optional[str] = None

    target_user_id: Optional[int] = None
    target_user_email: Optional[str] = None

    school_id: Optional[int] = None

    action: Optional[str] = None
    entity_type: Optional[str] = None

    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
