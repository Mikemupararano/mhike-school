from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole, UserStatus


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str
    school_id: Optional[int] = None

    # New multi-role field
    roles: list[UserRole] = Field(min_length=1)

    # Legacy compatibility field for any code path still expecting one role.
    # The service layer should prefer roles[].
    role: Optional[UserRole] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None

    # New multi-role update field
    roles: Optional[list[UserRole]] = None

    # Legacy compatibility field
    role: Optional[UserRole] = None

    status: Optional[UserStatus] = None
    is_active: Optional[bool] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: Optional[str] = None

    # Legacy field kept during transition
    role: UserRole

    # New source-of-truth field for frontend and permissions
    roles: list[UserRole]

    status: UserStatus
    school_id: Optional[int] = None
    school_name: Optional[str] = None
    is_active: bool
    created_at: datetime
