from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SqlEnum,
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
    from app.models.assessment import Assessment
    from app.models.user import User


class AssessmentResultPublicationStatus(str, Enum):
    """
    Lifecycle state for assessment-result publication.

    UNRELEASED
        Results are not visible to students or parents.

    SCHEDULED
        Results are configured for future release.

    PUBLISHED
        Results are currently released according to the configured
        student/parent visibility settings.

    WITHDRAWN
        A previously published result release has been withdrawn.

    Assessment-result publication is deliberately separate from
    ``Assessment.status``. An assessment may itself be PUBLISHED for
    candidate participation while its results remain UNRELEASED.
    """

    UNRELEASED = "unreleased"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"


class AssessmentResultPublication(Base):
    """
    Represent result-release configuration for one assessment.

    An assessment may have at most one result-publication record.

    This model controls when derived marks, percentages, grades and
    question-level information become visible outside staff workflows.

    Ordinary classroom assessments are teacher-publishable by default.

    Examples:
        - end-of-topic test
        - practical assessment
        - internal quiz
        - class test

    More controlled assessments may set ``requires_approval=True`` so a
    school can require administrative or SMT approval before publication.

    Publication authority itself is enforced in the service layer:

        - the course teacher may publish assessments they teach;
        - School Admin may publish within their school;
        - SMT may publish within their school;
        - Platform Admin may publish across schools.

    Approval is therefore optional governance, not a universal prerequisite.

    Marks and grades are not persisted here. They remain derived from the
    authoritative assessment marking, results and grading layers.
    """

    __tablename__ = "assessment_result_publications"

    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            name="uq_assessment_result_publication_assessment",
        ),
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # Assessment ownership
    # ------------------------------------------------------------------

    assessment_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assessments.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Publication lifecycle
    # ------------------------------------------------------------------

    status: Mapped[AssessmentResultPublicationStatus] = mapped_column(
        SqlEnum(
            AssessmentResultPublicationStatus,
            name="assessment_result_publication_status",
            values_callable=lambda enum_cls: [value.value for value in enum_cls],
            native_enum=False,
            validate_strings=True,
        ),
        default=AssessmentResultPublicationStatus.UNRELEASED,
        nullable=False,
        index=True,
    )

    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=True,
        index=True,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=True,
        index=True,
    )

    published_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    withdrawn_at: Mapped[datetime | None] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=True,
    )

    withdrawn_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    withdrawal_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Optional approval workflow
    # ------------------------------------------------------------------

    requires_approval: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        index=True,
    )

    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=True,
    )

    approved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    approval_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Audience visibility
    # ------------------------------------------------------------------

    visible_to_students: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        index=True,
    )

    visible_to_parents: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Result-content visibility
    # ------------------------------------------------------------------

    include_mark: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    include_percentage: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    include_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    include_question_breakdown: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Optional release message
    # ------------------------------------------------------------------

    release_message: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Creation audit
    # ------------------------------------------------------------------

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

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

    assessment: Mapped["Assessment"] = relationship(
        "Assessment",
        back_populates="result_publication",
        foreign_keys=[assessment_id],
        lazy="selectin",
    )

    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_id],
        lazy="selectin",
    )

    published_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[published_by_id],
        lazy="selectin",
    )

    withdrawn_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[withdrawn_by_id],
        lazy="selectin",
    )

    approved_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[approved_by_id],
        lazy="selectin",
    )

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def is_published(self) -> bool:
        """
        Return whether results are currently published.
        """

        return self.status == AssessmentResultPublicationStatus.PUBLISHED

    @property
    def is_scheduled(self) -> bool:
        """
        Return whether results are awaiting scheduled publication.
        """

        return self.status == AssessmentResultPublicationStatus.SCHEDULED

    @property
    def is_approved(self) -> bool:
        """
        Return whether required approval has been granted.

        Assessments that do not require approval are effectively approved
        for publication purposes.
        """

        if not self.requires_approval:
            return True

        return self.approved_at is not None

    @property
    def can_release(self) -> bool:
        """
        Return whether approval requirements permit result release.

        This property does not evaluate marking completeness or actor
        permissions; those remain service-layer concerns.
        """

        return self.is_approved

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            "<AssessmentResultPublication "
            f"id={self.id!r} "
            f"assessment_id={self.assessment_id!r} "
            f"status={self.status!r} "
            f"requires_approval={self.requires_approval!r} "
            f"visible_to_students={self.visible_to_students!r} "
            f"visible_to_parents={self.visible_to_parents!r}>"
        )
