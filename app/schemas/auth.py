from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole, UserStatus


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    school_id: Optional[int] = None
    full_name: Optional[str] = None

    # New multi-role field (PRIMARY)
    roles: list[UserRole] = Field(
        default_factory=lambda: [UserRole.STUDENT],
        min_length=1,
    )

    # Legacy compatibility field (will be removed later)
    role: Optional[UserRole] = None

    @field_validator("roles")
    @classmethod
    def validate_roles(cls, roles: list[UserRole]) -> list[UserRole]:
        """
        Prevent invalid combinations like:
        - platform_admin + school roles
        """
        if not roles:
            raise ValueError("At least one role is required.")

        has_platform_admin = UserRole.PLATFORM_ADMIN in roles
        has_school_role = any(
            role in roles
            for role in {
                UserRole.SCHOOL_ADMIN,
                UserRole.TEACHER,
                UserRole.STUDENT,
            }
        )

        if has_platform_admin and has_school_role:
            raise ValueError("platform_admin cannot be combined with school roles.")

        return roles


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

    # Legacy (temporary)
    role: Optional[UserRole] = None

    # New multi-role field (PRIMARY)
    roles: list[UserRole] = Field(default_factory=list)

    school_id: Optional[int] = None

    @field_validator("roles", mode="before")
    @classmethod
    def ensure_roles(cls, value, values):
        """
        Ensures backward compatibility:
        If roles[] is missing but role exists → convert to roles[]
        """
        if value:
            return value

        legacy_role = values.get("role")
        if legacy_role:
            return [legacy_role]

        return []


class CurrentUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: Optional[str] = None

    # Legacy field (temporary)
    role: Optional[UserRole] = None

    # New multi-role field (PRIMARY)
    roles: list[UserRole] = Field(default_factory=list)

    status: UserStatus
    school_id: Optional[int] = None
    is_active: bool

    @field_validator("roles", mode="before")
    @classmethod
    def ensure_roles(cls, value, values):
        """
        Ensure roles[] is always populated even if coming from legacy DB field
        """
        if value:
            return value

        legacy_role = values.get("role")
        if legacy_role:
            return [legacy_role]

        return []

    @property
    def role_names(self) -> list[str]:
        return [role.value for role in self.roles]
