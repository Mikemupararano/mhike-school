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


class UserStatus(str, Enum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    PENDING_ERASURE = "pending_erasure"
    ANONYMISED = "anonymised"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", "school_id", name="uq_users_email_school_id"),
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

    # Keep this temporarily during the migration to multi-role support.
    # Existing code may still depend on it until services/schemas/frontend
    # are fully switched over to roles[].
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(
            UserRole,
            name="user_role",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
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
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
            native_enum=False,
            validate_strings=True,
        ),
        default=UserStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

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
    )

    @property
    def roles(self) -> list[str]:
        """
        Transitional multi-role accessor.

        During migration:
        - Prefer roles from the user_roles association table if present
        - Fall back to the legacy single role column otherwise
        """
        if self.user_roles:
            return [assignment.role.value for assignment in self.user_roles]
        return [self.role.value] if self.role else []

    @property
    def is_platform_admin(self) -> bool:
        return UserRole.PLATFORM_ADMIN.value in self.roles

    @property
    def is_school_admin(self) -> bool:
        return UserRole.SCHOOL_ADMIN.value in self.roles

    @property
    def is_teacher(self) -> bool:
        return UserRole.TEACHER.value in self.roles

    @property
    def is_student(self) -> bool:
        return UserRole.STUDENT.value in self.roles

    @property
    def is_school_staff(self) -> bool:
        return any(
            role in self.roles
            for role in {
                UserRole.SCHOOL_ADMIN.value,
                UserRole.TEACHER.value,
            }
        )

    @property
    def can_teach(self) -> bool:
        return any(
            role in self.roles
            for role in {
                UserRole.SCHOOL_ADMIN.value,
                UserRole.TEACHER.value,
            }
        )
