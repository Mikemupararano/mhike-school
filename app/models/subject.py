from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.school import School


class Subject(Base):
    """
    Represent a canonical academic subject within one school.

    A subject represents the broad academic discipline, for example:

        - Physics
        - Chemistry
        - Biology
        - Mathematics
        - English

    It is intentionally distinct from a Course.

    A Course represents a particular programme, qualification or
    specification such as:

        - AQA GCSE Physics
        - OCR A Level Physics A
        - AQA A Level Physics

    Keeping Subject and Course separate provides a stable academic taxonomy
    for assessment, curriculum analysis, reporting and future MIS
    integrations.

    Subject records are school-scoped. The same subject name or code may
    therefore exist independently in different schools.
    """

    __tablename__ = "subjects"

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "name",
            name="uq_subject_school_name",
        ),
        UniqueConstraint(
            "school_id",
            "code",
            name="uq_subject_school_code",
        ),
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # School scope
    # ------------------------------------------------------------------

    school_id: Mapped[int] = mapped_column(
        ForeignKey(
            "schools.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Subject metadata
    # ------------------------------------------------------------------

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Audit timestamps
    # ------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    school: Mapped["School"] = relationship(
        "School",
        back_populates="subjects",
        foreign_keys=[school_id],
        lazy="selectin",
    )

    courses: Mapped[list["Course"]] = relationship(
        "Course",
        back_populates="subject",
        foreign_keys="Course.subject_id",
        lazy="selectin",
    )

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            "<Subject "
            f"id={self.id!r} "
            f"name={self.name!r} "
            f"code={self.code!r} "
            f"school_id={self.school_id!r} "
            f"is_active={self.is_active!r}>"
        )
