from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, Enum):
    PLATFORM_ADMIN = "platform_admin"
    SCHOOL_ADMIN = "school_admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"


class UserStatus(str, Enum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    PENDING_ERASURE = "pending_erasure"
    ANONYMISED = "anonymised"


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        UniqueConstraint(
            "email",
            "school_id",
            name="uq_users_email_school_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    email: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )

    hashed_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    role: Mapped[UserRole] = mapped_column(
        SqlEnum(
            UserRole,
            name="user_role",
            values_callable=lambda enum_cls: [role.value for role in enum_cls],
            native_enum=False,
            validate_strings=True,
        ),
        default=UserRole.STUDENT,
        nullable=False,
        index=True,
    )

    status: Mapped[UserStatus] = mapped_column(
        SqlEnum(
            UserStatus,
            name="user_status",
            values_callable=lambda enum_cls: [status.value for status in enum_cls],
            native_enum=False,
            validate_strings=True,
        ),
        default=UserStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    school_id: Mapped[int | None] = mapped_column(
        ForeignKey("schools.id"),
        nullable=True,
        index=True,
    )

    deletion_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    anonymised_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    retention_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    school: Mapped["School | None"] = relationship(
        "School",
        back_populates="users",
    )

    classes_taught: Mapped[list["ClassGroup"]] = relationship(
        "ClassGroup",
        back_populates="teacher",
        foreign_keys="ClassGroup.teacher_id",
    )

    user_roles: Mapped[list["UserRoleAssignment"]] = relationship(
        "UserRoleAssignment",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def roles(self) -> list[str]:
        if self.user_roles:
            return sorted(
                {
                    (
                        assignment.role.value
                        if isinstance(assignment.role, UserRole)
                        else str(assignment.role)
                    )
                    for assignment in self.user_roles
                }
            )

        return [self.role.value] if self.role else []

    @property
    def primary_role(self) -> str | None:
        if self.role:
            return self.role.value

        return self.roles[0] if self.roles else None

    def has_role(self, role: UserRole | str) -> bool:
        role_value = role.value if isinstance(role, UserRole) else role
        return role_value in self.roles

    def has_any_role(self, roles: list[UserRole | str] | set[UserRole | str]) -> bool:
        role_values = {
            role.value if isinstance(role, UserRole) else role for role in roles
        }

        return bool(set(self.roles).intersection(role_values))

    @property
    def is_platform_admin(self) -> bool:
        return self.has_role(UserRole.PLATFORM_ADMIN)

    @property
    def is_school_admin(self) -> bool:
        return self.has_role(UserRole.SCHOOL_ADMIN)

    @property
    def is_teacher(self) -> bool:
        return self.has_role(UserRole.TEACHER)

    @property
    def is_student(self) -> bool:
        return self.has_role(UserRole.STUDENT)

    @property
    def is_parent(self) -> bool:
        return self.has_role(UserRole.PARENT)

    @property
    def is_school_staff(self) -> bool:
        return self.has_any_role(
            {
                UserRole.SCHOOL_ADMIN,
                UserRole.TEACHER,
            }
        )

    @property
    def can_teach(self) -> bool:
        return self.has_any_role(
            {
                UserRole.SCHOOL_ADMIN,
                UserRole.TEACHER,
            }
        )
