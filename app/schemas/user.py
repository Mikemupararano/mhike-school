from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.user import UserRole, UserStatus


SCHOOL_ROLES = {
    UserRole.SCHOOL_ADMIN,
    UserRole.TEACHER,
    UserRole.STUDENT,
}


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(min_length=6)
    school_id: Optional[int] = None

    # Primary multi-role field.
    # Supports users such as ["school_admin", "teacher"].
    roles: list[UserRole] = Field(
        default_factory=lambda: [UserRole.STUDENT],
        min_length=1,
    )

    # Legacy compatibility field.
    # Derived from roles using priority order if omitted.
    role: Optional[UserRole] = None

    @model_validator(mode="after")
    def sync_and_validate_roles(self) -> "UserCreate":
        self.roles = _dedupe_roles(self.roles)

        _validate_role_combination(self.roles, self.school_id)

        if self.role is None:
            self.role = _get_primary_role(self.roles)
        elif self.role not in self.roles:
            self.roles = _dedupe_roles([self.role, *self.roles])

        return self


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    school_id: Optional[int] = None

    # Primary multi-role update field.
    roles: Optional[list[UserRole]] = None

    # Legacy compatibility field.
    role: Optional[UserRole] = None

    status: Optional[UserStatus] = None
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def sync_and_validate_roles(self) -> "UserUpdate":
        if self.roles is not None:
            if len(self.roles) == 0:
                raise ValueError("roles cannot be empty.")

            self.roles = _dedupe_roles(self.roles)

            if self.role is None:
                self.role = _get_primary_role(self.roles)
            elif self.role not in self.roles:
                self.roles = _dedupe_roles([self.role, *self.roles])

        elif self.role is not None:
            self.roles = [self.role]

        if self.roles is not None:
            _validate_role_combination(self.roles, self.school_id)

        return self


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: Optional[str] = None

    # Transitional legacy primary role.
    role: UserRole

    # Primary frontend field.
    roles: list[UserRole] = Field(default_factory=list)

    status: UserStatus
    school_id: Optional[int] = None
    school_name: Optional[str] = None
    is_active: bool
    created_at: datetime


def _dedupe_roles(roles: list[UserRole]) -> list[UserRole]:
    seen: set[UserRole] = set()
    deduped: list[UserRole] = []

    for role in roles:
        if role not in seen:
            deduped.append(role)
            seen.add(role)

    return deduped


def _get_primary_role(roles: list[UserRole]) -> UserRole:
    priority = [
        UserRole.PLATFORM_ADMIN,
        UserRole.SCHOOL_ADMIN,
        UserRole.TEACHER,
        UserRole.STUDENT,
    ]

    for role in priority:
        if role in roles:
            return role

    return UserRole.STUDENT


def _validate_role_combination(
    roles: list[UserRole],
    school_id: int | None,
) -> None:
    has_platform_admin = UserRole.PLATFORM_ADMIN in roles
    has_school_role = bool(set(roles).intersection(SCHOOL_ROLES))

    if has_platform_admin and has_school_role:
        raise ValueError("platform_admin cannot be combined with school roles.")

    if has_platform_admin and school_id is not None:
        raise ValueError("platform_admin must not belong to a school.")

    if has_school_role and school_id is None:
        raise ValueError("school_id is required for school users.")
