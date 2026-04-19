from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.user import UserRole, UserStatus


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str
    school_id: Optional[int] = None

    # New multi-role field
    roles: list[UserRole] = Field(min_length=1)

    # Legacy compatibility field.
    # If omitted, it will be derived from roles[0].
    role: Optional[UserRole] = None

    @model_validator(mode="after")
    def sync_role_fields(self) -> "UserCreate":
        if not self.roles:
            raise ValueError("At least one role is required.")

        if self.role is None:
            self.role = self.roles[0]
        elif self.role not in self.roles:
            self.roles = [self.role, *[r for r in self.roles if r != self.role]]

        return self


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None

    # New multi-role update field
    roles: Optional[list[UserRole]] = None

    # Legacy compatibility field
    role: Optional[UserRole] = None

    status: Optional[UserStatus] = None
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def sync_role_fields(self) -> "UserUpdate":
        if self.roles is not None and len(self.roles) == 0:
            raise ValueError("roles cannot be empty.")

        if self.roles is not None:
            if self.role is None:
                self.role = self.roles[0]
            elif self.role not in self.roles:
                self.roles = [self.role, *[r for r in self.roles if r != self.role]]

        return self


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: Optional[str] = None

    # Legacy primary role kept during transition
    role: UserRole

    # New source-of-truth field for frontend and permissions
    roles: list[UserRole]

    status: UserStatus
    school_id: Optional[int] = None
    school_name: Optional[str] = None
    is_active: bool
    created_at: datetime
