from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole, UserStatus


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    school_id: Optional[int] = None
    full_name: Optional[str] = None

    # New multi-role field
    roles: list[UserRole] = Field(
        default_factory=lambda: [UserRole.STUDENT],
        min_length=1,
    )

    # Legacy compatibility field
    role: Optional[UserRole] = UserRole.STUDENT


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    school_id: Optional[int] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: int
    email: Optional[EmailStr] = None

    # Legacy compatibility field
    role: Optional[UserRole] = None

    # New multi-role field
    roles: list[UserRole] = Field(default_factory=list)

    school_id: Optional[int] = None


class CurrentUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: Optional[str] = None

    # Legacy field kept during transition
    role: UserRole

    # New multi-role field
    roles: list[UserRole]

    status: UserStatus
    school_id: Optional[int] = None
    is_active: bool
