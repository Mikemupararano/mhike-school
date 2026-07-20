from __future__ import annotations

from collections.abc import Iterable
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
    """
    Canonical application roles.

    Only these values are stored in users.role.

    Additional responsibilities such as SMT, Headmaster, Head of Year,
    Housemaster and Tutor are assigned through the user_roles table and are
    treated as secondary roles rather than primary authentication roles.
    """

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

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    hashed_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Legacy primary role.
    # Additional responsibilities are stored in user_roles.
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
        ForeignKey(
            "schools.id",
            ondelete="SET NULL",
        ),
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
    # ------------------------------------------------------------------
    # Role normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_role_value(
        role: UserRole | str | None,
    ) -> str | None:
        """
        Return a canonical role value.

        This allows imported data, legacy code and different terminology to
        resolve to a single consistent value without requiring additional
        values in the UserRole enum.
        """

        if role is None:
            return None

        raw_value = role.value if isinstance(role, UserRole) else str(role)

        normalised = (
            raw_value.strip()
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )

        aliases = {
            "platformadmin": UserRole.PLATFORM_ADMIN.value,
            "platform_administrator": UserRole.PLATFORM_ADMIN.value,
            "schooladmin": UserRole.SCHOOL_ADMIN.value,
            "school_administrator": UserRole.SCHOOL_ADMIN.value,
            "senior_management_team": "smt",
            "senior_leadership_team": "smt",
            "slt": "smt",
            "headteacher": "headmaster",
            "head_teacher": "headmaster",
            "principal": "headmaster",
            "head_of_school": "headmaster",
            "headofyear": "head_of_year",
            "head_year": "head_of_year",
            "hoy": "head_of_year",
            "house_master": "housemaster",
            "houseparent": "housemaster",
            "form_tutor": "tutor",
            "form_teacher": "tutor",
            "class_teacher": UserRole.TEACHER.value,
            "pupil": UserRole.STUDENT.value,
            "guardian": UserRole.PARENT.value,
        }

        return aliases.get(normalised, normalised)

    @property
    def roles(self) -> list[str]:
        """
        Return every role or responsibility held by the user.

        Combines the legacy primary role with all entries in user_roles while
        removing duplicates.
        """

        role_values: set[str] = set()

        primary_role_value = self._normalise_role_value(self.role)

        if primary_role_value:
            role_values.add(primary_role_value)

        for assignment in self.user_roles or []:
            assignment_role_value = self._normalise_role_value(
                assignment.role,
            )

            if assignment_role_value:
                role_values.add(assignment_role_value)

        return sorted(role_values)

    @property
    def primary_role(self) -> str | None:
        primary_role_value = self._normalise_role_value(self.role)

        if primary_role_value:
            return primary_role_value

        return self.roles[0] if self.roles else None

    def has_role(
        self,
        role: UserRole | str,
    ) -> bool:
        role_value = self._normalise_role_value(role)

        if role_value is None:
            return False

        return role_value in self.roles

    def has_any_role(
        self,
        roles: Iterable[UserRole | str],
    ) -> bool:
        role_values = {
            role_value
            for role in roles
            if (role_value := self._normalise_role_value(role)) is not None
        }

        return bool(role_values.intersection(self.roles))

    # ------------------------------------------------------------------
    # Individual role helpers
    # ------------------------------------------------------------------

    @property
    def is_platform_admin(self) -> bool:
        return self.has_role(UserRole.PLATFORM_ADMIN)

    @property
    def is_school_admin(self) -> bool:
        return self.has_role(UserRole.SCHOOL_ADMIN)

    @property
    def is_smt(self) -> bool:
        return self.has_any_role(
            {
                "smt",
                UserRole.SCHOOL_ADMIN,
                UserRole.PLATFORM_ADMIN,
            }
        )

    @property
    def is_headmaster(self) -> bool:
        return self.has_role("headmaster")

    @property
    def is_headteacher(self) -> bool:
        """
        Backwards-compatible alias.
        """
        return self.is_headmaster

    @property
    def is_head_of_year(self) -> bool:
        return self.has_role("head_of_year")

    @property
    def is_housemaster(self) -> bool:
        return self.has_role("housemaster")

    @property
    def is_teacher(self) -> bool:
        return self.has_role(UserRole.TEACHER)

    @property
    def is_tutor(self) -> bool:
        return self.has_role("tutor")

    @property
    def is_student(self) -> bool:
        return self.has_role(UserRole.STUDENT)

    @property
    def is_parent(self) -> bool:
        return self.has_role(UserRole.PARENT)

    # ------------------------------------------------------------------
    # Permission group helpers
    # ------------------------------------------------------------------

    @property
    def is_school_staff(self) -> bool:
        return self.has_any_role(
            {
                UserRole.SCHOOL_ADMIN,
                "smt",
                "headmaster",
                "head_of_year",
                "housemaster",
                UserRole.TEACHER,
                "tutor",
            }
        )

    @property
    def is_pastoral_staff(self) -> bool:
        return self.has_any_role(
            {
                UserRole.SCHOOL_ADMIN,
                "smt",
                "headmaster",
                "head_of_year",
                "housemaster",
                "tutor",
            }
        )

    @property
    def can_teach(self) -> bool:
        """
        Whether the user may be assigned as the teacher of a class.

        Senior and pastoral staff may also teach. More specific restrictions
        can still be enforced at service or endpoint level.
        """

        return self.has_any_role(
            {
                UserRole.SCHOOL_ADMIN,
                "smt",
                "headmaster",
                "head_of_year",
                "housemaster",
                UserRole.TEACHER,
                "tutor",
            }
        )

    @property
    def can_review_reports(self) -> bool:
        """
        Whether the user may review or edit reports after teacher submission.

        This includes pastoral and senior staff who may contribute comments or
        make corrections during the review workflow.
        """

        return self.has_any_role(
            {
                UserRole.PLATFORM_ADMIN,
                UserRole.SCHOOL_ADMIN,
                "smt",
                "headmaster",
                "head_of_year",
                "housemaster",
                "tutor",
            }
        )

    @property
    def can_approve_reports(self) -> bool:
        """
        Whether the user may give final SMT approval.

        Final approval is restricted to Platform Admin, School Admin and SMT.
        A Headmaster may review, edit, print and download reports, but does not
        approve unless they also hold SMT or School Admin responsibility.
        """

        return self.has_any_role(
            {
                UserRole.PLATFORM_ADMIN,
                UserRole.SCHOOL_ADMIN,
                "smt",
            }
        )

    @property
    def can_publish_reports(self) -> bool:
        """
        Whether the user may publish approved reports.

        Publishing is restricted to Platform Admin, School Admin and SMT.
        """

        return self.has_any_role(
            {
                UserRole.PLATFORM_ADMIN,
                UserRole.SCHOOL_ADMIN,
                "smt",
            }
        )

    def __repr__(self) -> str:
        return (
            f"<User "
            f"id={self.id} "
            f"email={self.email!r} "
            f"roles={self.roles}>"
        )
