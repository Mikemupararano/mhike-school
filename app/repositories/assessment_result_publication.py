from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment_result_publication import (
    AssessmentResultPublication,
    AssessmentResultPublicationStatus,
)


class AssessmentResultPublicationRepository:
    """
    Repository for assessment-result publication configuration.

    This layer handles persistence only.

    Business rules such as:

        - teacher ownership;
        - school isolation;
        - approval requirements;
        - marking completeness;
        - scheduled release;
        - student/parent visibility;

    belong in the service layer.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    async def get_by_id(
        self,
        publication_id: int,
    ) -> AssessmentResultPublication | None:
        """
        Return one publication record.
        """

        stmt = (
            select(AssessmentResultPublication)
            .options(
                selectinload(
                    AssessmentResultPublication.assessment,
                ),
                selectinload(
                    AssessmentResultPublication.created_by,
                ),
                selectinload(
                    AssessmentResultPublication.published_by,
                ),
                selectinload(
                    AssessmentResultPublication.withdrawn_by,
                ),
                selectinload(
                    AssessmentResultPublication.approved_by,
                ),
            )
            .where(
                AssessmentResultPublication.id == publication_id,
            )
        )

        result = await self.db.execute(stmt)

        return result.scalar_one_or_none()

    async def get_for_assessment(
        self,
        assessment_id: int,
    ) -> AssessmentResultPublication | None:
        """
        Return publication configuration for one assessment.
        """

        stmt = (
            select(AssessmentResultPublication)
            .options(
                selectinload(
                    AssessmentResultPublication.assessment,
                ),
                selectinload(
                    AssessmentResultPublication.created_by,
                ),
                selectinload(
                    AssessmentResultPublication.published_by,
                ),
                selectinload(
                    AssessmentResultPublication.withdrawn_by,
                ),
                selectinload(
                    AssessmentResultPublication.approved_by,
                ),
            )
            .where(
                AssessmentResultPublication.assessment_id == assessment_id,
            )
        )

        result = await self.db.execute(stmt)

        return result.scalar_one_or_none()

    async def get_published_for_assessment(
        self,
        assessment_id: int,
    ) -> AssessmentResultPublication | None:
        """
        Return the currently published release for an assessment.
        """

        stmt = select(AssessmentResultPublication).where(
            AssessmentResultPublication.assessment_id == assessment_id,
            AssessmentResultPublication.status
            == AssessmentResultPublicationStatus.PUBLISHED,
        )

        result = await self.db.execute(stmt)

        return result.scalar_one_or_none()

    async def list_due_scheduled_publications(
        self,
        *,
        now: datetime,
    ) -> list[AssessmentResultPublication]:
        """
        Return scheduled publications whose release time has arrived.

        This supports a future Celery/background publication workflow.
        """

        stmt = (
            select(AssessmentResultPublication)
            .where(
                AssessmentResultPublication.status
                == AssessmentResultPublicationStatus.SCHEDULED,
                AssessmentResultPublication.scheduled_for.is_not(
                    None,
                ),
                AssessmentResultPublication.scheduled_for <= now,
            )
            .order_by(
                AssessmentResultPublication.scheduled_for.asc(),
                AssessmentResultPublication.id.asc(),
            )
        )

        result = await self.db.execute(stmt)

        return list(
            result.scalars().all(),
        )

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        assessment_id: int,
        created_by_id: int,
        requires_approval: bool = False,
        visible_to_students: bool = True,
        visible_to_parents: bool = True,
        include_mark: bool = True,
        include_percentage: bool = True,
        include_grade: bool = True,
        include_question_breakdown: bool = False,
        release_message: str | None = None,
    ) -> AssessmentResultPublication:
        """
        Create one unreleased publication configuration.
        """

        publication = AssessmentResultPublication(
            assessment_id=assessment_id,
            status=(AssessmentResultPublicationStatus.UNRELEASED),
            requires_approval=requires_approval,
            visible_to_students=visible_to_students,
            visible_to_parents=visible_to_parents,
            include_mark=include_mark,
            include_percentage=include_percentage,
            include_grade=include_grade,
            include_question_breakdown=(include_question_breakdown),
            release_message=release_message,
            created_by_id=created_by_id,
        )

        self.db.add(
            publication,
        )

        await self.db.flush()

        return publication

    # ------------------------------------------------------------------
    # Configuration updates
    # ------------------------------------------------------------------

    async def flush(
        self,
    ) -> None:
        """
        Flush pending publication changes.
        """

        await self.db.flush()

    async def refresh(
        self,
        publication: AssessmentResultPublication,
    ) -> AssessmentResultPublication:
        """
        Refresh one publication record.
        """

        await self.db.refresh(
            publication,
        )

        return publication

    # ------------------------------------------------------------------
    # Publication lifecycle
    # ------------------------------------------------------------------

    async def mark_scheduled(
        self,
        publication: AssessmentResultPublication,
        *,
        scheduled_for: datetime,
    ) -> AssessmentResultPublication:
        """
        Mark a publication as scheduled.
        """

        publication.status = AssessmentResultPublicationStatus.SCHEDULED

        publication.scheduled_for = scheduled_for

        publication.published_at = None
        publication.published_by_id = None

        publication.withdrawn_at = None
        publication.withdrawn_by_id = None
        publication.withdrawal_reason = None

        await self.db.flush()

        return publication

    async def mark_published(
        self,
        publication: AssessmentResultPublication,
        *,
        published_by_id: int,
        published_at: datetime,
    ) -> AssessmentResultPublication:
        """
        Mark results as published immediately.
        """

        publication.status = AssessmentResultPublicationStatus.PUBLISHED

        publication.published_at = published_at
        publication.published_by_id = published_by_id

        publication.scheduled_for = None

        publication.withdrawn_at = None
        publication.withdrawn_by_id = None
        publication.withdrawal_reason = None

        await self.db.flush()

        return publication

    async def mark_withdrawn(
        self,
        publication: AssessmentResultPublication,
        *,
        withdrawn_by_id: int,
        withdrawn_at: datetime,
        withdrawal_reason: str | None = None,
    ) -> AssessmentResultPublication:
        """
        Withdraw a current or scheduled result release.
        """

        publication.status = AssessmentResultPublicationStatus.WITHDRAWN

        publication.withdrawn_at = withdrawn_at
        publication.withdrawn_by_id = withdrawn_by_id
        publication.withdrawal_reason = withdrawal_reason

        publication.scheduled_for = None

        await self.db.flush()

        return publication

    async def mark_unreleased(
        self,
        publication: AssessmentResultPublication,
    ) -> AssessmentResultPublication:
        """
        Return publication configuration to unreleased state.

        Historical publication and withdrawal audit fields are preserved
        unless the service explicitly clears them.
        """

        publication.status = AssessmentResultPublicationStatus.UNRELEASED

        publication.scheduled_for = None

        await self.db.flush()

        return publication

    # ------------------------------------------------------------------
    # Approval lifecycle
    # ------------------------------------------------------------------

    async def mark_approved(
        self,
        publication: AssessmentResultPublication,
        *,
        approved_by_id: int,
        approved_at: datetime,
        approval_note: str | None = None,
    ) -> AssessmentResultPublication:
        """
        Record publication approval.
        """

        publication.approved_at = approved_at
        publication.approved_by_id = approved_by_id
        publication.approval_note = approval_note

        await self.db.flush()

        return publication

    async def clear_approval(
        self,
        publication: AssessmentResultPublication,
    ) -> AssessmentResultPublication:
        """
        Remove existing publication approval.
        """

        publication.approved_at = None
        publication.approved_by_id = None
        publication.approval_note = None

        await self.db.flush()

        return publication

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    async def delete(
        self,
        publication: AssessmentResultPublication,
    ) -> None:
        """
        Delete publication configuration.
        """

        await self.db.delete(
            publication,
        )

        await self.db.flush()
