from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserRole(str, Enum):
    PLATFORM_ADMIN = "platform_admin"
    SCHOOL_ADMIN = "school_admin"
    TEACHER = "teacher"
    STUDENT = "student"


class UserStatus(str, Enum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    PENDING_ERASURE = "pending_erasure"
    ANONYMISED = "anonymised"


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    school_id: Optional[int] = None
    full_name: Optional[str] = None
    role: UserRole = UserRole.STUDENT


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    school_id: Optional[int] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: int
    email: EmailStr
    role: UserRole
    school_id: Optional[int] = None


class CurrentUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole
    status: UserStatus
    school_id: Optional[int] = None
    is_active: bool
