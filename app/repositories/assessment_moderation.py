from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment_candidate import AssessmentScript
from app.models.assessment_moderation import (
    AssessmentModerationItem,
    AssessmentModerationItemOutcome,
    AssessmentModerationOutcome,
    AssessmentModerationReview,
    AssessmentModerationReviewStatus,
    AssessmentModerationSamplingMethod,
)


class AssessmentModerationRepository:
    """
    Persistence operations for assessment moderation and QA history.

    The repository owns database querying and persistence only.

    Business rules such as permissions, valid workflow transitions,
    moderation sampling policy, mark adjustment policy, and interaction with
    authoritative AssessmentResultOutcome records belong in the service
    layer.

    Repository methods deliberately do not commit transactions. Callers
    decide transaction boundaries.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Review query construction
    # ------------------------------------------------------------------

    @staticmethod
    def _review_query(
        *,
        include_relationships: bool = False,
        include_items: bool = False,
    ):
        """
        Build the base moderation-review query.

        Relationship loading is explicit so service methods can safely
        request complete moderation records without triggering accidental
        asynchronous lazy loading.
        """

        stmt = select(
            AssessmentModerationReview,
        )

        if include_relationships:
            stmt = stmt.options(
                selectinload(
                    AssessmentModerationReview.assessment,
                ),
                selectinload(
                    AssessmentModerationReview.candidate,
                ),
                selectinload(
                    AssessmentModerationReview.script,
                ),
                selectinload(
                    AssessmentModerationReview.moderator,
                ),
                selectinload(
                    AssessmentModerationReview.initiated_by,
                ),
                selectinload(
                    AssessmentModerationReview.cancelled_by,
                ),
            )

        if include_items:
            stmt = stmt.options(
                selectinload(
                    AssessmentModerationReview.items,
                ),
            )

        return stmt

    # ------------------------------------------------------------------
    # Review reads
    # ------------------------------------------------------------------

    async def get_review_by_id(
        self,
        review_id: int,
        *,
        include_relationships: bool = False,
        include_items: bool = False,
    ) -> AssessmentModerationReview | None:
        """
        Return one moderation review by primary key.
        """

        stmt = self._review_query(
            include_relationships=include_relationships,
            include_items=include_items,
        ).where(
            AssessmentModerationReview.id == review_id,
        )

        result = await self.db.execute(
            stmt,
        )

        return result.scalars().unique().one_or_none()

    async def get_review_by_id_for_school(
        self,
        review_id: int,
        school_id: int,
        *,
        include_relationships: bool = False,
        include_items: bool = False,
    ) -> AssessmentModerationReview | None:
        """
        Return one moderation review scoped to a school.
        """

        stmt = self._review_query(
            include_relationships=include_relationships,
            include_items=include_items,
        ).where(
            AssessmentModerationReview.id == review_id,
            AssessmentModerationReview.school_id == school_id,
        )

        result = await self.db.execute(
            stmt,
        )

        return result.scalars().unique().one_or_none()

    async def list_reviews_for_script(
        self,
        script_id: int,
        *,
        include_relationships: bool = False,
        include_items: bool = False,
    ) -> list[AssessmentModerationReview]:
        """
        Return moderation history for one script in review-number order.
        """

        stmt = (
            self._review_query(
                include_relationships=include_relationships,
                include_items=include_items,
            )
            .where(
                AssessmentModerationReview.script_id == script_id,
            )
            .order_by(
                AssessmentModerationReview.review_number.asc(),
                AssessmentModerationReview.id.asc(),
            )
        )

        result = await self.db.execute(
            stmt,
        )

        return list(
            result.scalars().unique().all(),
        )

    async def list_reviews_for_candidate(
        self,
        candidate_id: int,
        *,
        include_relationships: bool = False,
        include_items: bool = False,
    ) -> list[AssessmentModerationReview]:
        """
        Return moderation reviews belonging to one candidate.
        """

        stmt = (
            self._review_query(
                include_relationships=include_relationships,
                include_items=include_items,
            )
            .where(
                AssessmentModerationReview.candidate_id == candidate_id,
            )
            .order_by(
                AssessmentModerationReview.created_at.asc(),
                AssessmentModerationReview.id.asc(),
            )
        )

        result = await self.db.execute(
            stmt,
        )

        return list(
            result.scalars().unique().all(),
        )

    async def list_reviews_for_assessment(
        self,
        assessment_id: int,
        *,
        school_id: int | None = None,
        status: AssessmentModerationReviewStatus | None = None,
        outcome: AssessmentModerationOutcome | None = None,
        include_relationships: bool = False,
        include_items: bool = False,
    ) -> list[AssessmentModerationReview]:
        """
        Return moderation reviews for an assessment.

        Optional school, status and outcome filters support both normal
        school-scoped use and future platform-level QA reporting.
        """

        stmt = self._review_query(
            include_relationships=include_relationships,
            include_items=include_items,
        ).where(
            AssessmentModerationReview.assessment_id == assessment_id,
        )

        if school_id is not None:
            stmt = stmt.where(
                AssessmentModerationReview.school_id == school_id,
            )

        if status is not None:
            stmt = stmt.where(
                AssessmentModerationReview.status == status,
            )

        if outcome is not None:
            stmt = stmt.where(
                AssessmentModerationReview.outcome == outcome,
            )

        stmt = stmt.order_by(
            AssessmentModerationReview.created_at.asc(),
            AssessmentModerationReview.id.asc(),
        )

        result = await self.db.execute(
            stmt,
        )

        return list(
            result.scalars().unique().all(),
        )

    async def list_reviews_for_moderator(
        self,
        moderator_id: int,
        *,
        school_id: int | None = None,
        status: AssessmentModerationReviewStatus | None = None,
        include_relationships: bool = False,
        include_items: bool = False,
    ) -> list[AssessmentModerationReview]:
        """
        Return moderation reviews assigned to one moderator.
        """

        stmt = self._review_query(
            include_relationships=include_relationships,
            include_items=include_items,
        ).where(
            AssessmentModerationReview.moderator_id == moderator_id,
        )

        if school_id is not None:
            stmt = stmt.where(
                AssessmentModerationReview.school_id == school_id,
            )

        if status is not None:
            stmt = stmt.where(
                AssessmentModerationReview.status == status,
            )

        stmt = stmt.order_by(
            AssessmentModerationReview.created_at.asc(),
            AssessmentModerationReview.id.asc(),
        )

        result = await self.db.execute(
            stmt,
        )

        return list(
            result.scalars().unique().all(),
        )

    # ------------------------------------------------------------------
    # Review numbering
    # ------------------------------------------------------------------

    async def get_next_review_number(
        self,
        script_id: int,
    ) -> int:
        """
        Return the next moderation review number for a script.

        The parent AssessmentScript row is locked before calculating the next
        number. Repository callers that create reviews through this method
        therefore serialise review-number allocation for the same script
        within the current transaction.

        The database unique constraint on ``(script_id, review_number)``
        remains the final integrity guarantee.
        """

        script_stmt = (
            select(
                AssessmentScript.id,
            )
            .where(
                AssessmentScript.id == script_id,
            )
            .with_for_update()
        )

        script_result = await self.db.execute(
            script_stmt,
        )

        if script_result.scalar_one_or_none() is None:
            raise ValueError(
                "Assessment script does not exist.",
            )

        stmt = select(
            func.max(
                AssessmentModerationReview.review_number,
            ),
        ).where(
            AssessmentModerationReview.script_id == script_id,
        )

        result = await self.db.execute(
            stmt,
        )

        current_max = result.scalar_one_or_none()

        if current_max is None:
            return 1

        return int(current_max) + 1

    # ------------------------------------------------------------------
    # Review persistence
    # ------------------------------------------------------------------

    async def create_review(
        self,
        *,
        school_id: int,
        assessment_id: int,
        candidate_id: int,
        script_id: int,
        moderator_id: int,
        initiated_by_id: int,
        sampling_method: AssessmentModerationSamplingMethod = (
            AssessmentModerationSamplingMethod.MANUAL
        ),
        reason: str | None = None,
        notes: str | None = None,
        sample_description: str | None = None,
        status: AssessmentModerationReviewStatus = (
            AssessmentModerationReviewStatus.PENDING
        ),
        outcome: AssessmentModerationOutcome | None = None,
        review_number: int | None = None,
    ) -> AssessmentModerationReview:
        """
        Create one moderation review.

        When ``review_number`` is omitted, the next number is allocated while
        holding a row lock on the parent script.

        No transaction commit occurs here.
        """

        if review_number is None:
            review_number = await self.get_next_review_number(
                script_id,
            )

        review = AssessmentModerationReview(
            school_id=school_id,
            assessment_id=assessment_id,
            candidate_id=candidate_id,
            script_id=script_id,
            review_number=review_number,
            status=status,
            outcome=outcome,
            sampling_method=sampling_method,
            moderator_id=moderator_id,
            initiated_by_id=initiated_by_id,
            reason=reason,
            notes=notes,
            sample_description=sample_description,
        )

        self.db.add(
            review,
        )

        await self.db.flush()
        await self.db.refresh(
            review,
        )

        return review

    async def save_review(
        self,
        review: AssessmentModerationReview,
    ) -> AssessmentModerationReview:
        """
        Flush changes made to an existing moderation review.

        Workflow validation belongs to the service layer.
        """

        self.db.add(
            review,
        )

        await self.db.flush()
        await self.db.refresh(
            review,
        )

        return review

    # ------------------------------------------------------------------
    # Item query construction
    # ------------------------------------------------------------------

    @staticmethod
    def _item_query(
        *,
        include_relationships: bool = False,
    ):
        """
        Build the base moderation-item query.
        """

        stmt = select(
            AssessmentModerationItem,
        )

        if include_relationships:
            stmt = stmt.options(
                selectinload(
                    AssessmentModerationItem.review,
                ),
                selectinload(
                    AssessmentModerationItem.response,
                ),
                selectinload(
                    AssessmentModerationItem.marking_decision,
                ),
                selectinload(
                    AssessmentModerationItem.reviewed_by,
                ),
            )

        return stmt

    # ------------------------------------------------------------------
    # Item reads
    # ------------------------------------------------------------------

    async def get_item_by_id(
        self,
        item_id: int,
        *,
        include_relationships: bool = False,
    ) -> AssessmentModerationItem | None:
        """
        Return one moderation item by primary key.
        """

        stmt = self._item_query(
            include_relationships=include_relationships,
        ).where(
            AssessmentModerationItem.id == item_id,
        )

        result = await self.db.execute(
            stmt,
        )

        return result.scalars().unique().one_or_none()

    async def get_item_by_id_for_school(
        self,
        item_id: int,
        school_id: int,
        *,
        include_relationships: bool = False,
    ) -> AssessmentModerationItem | None:
        """
        Return one moderation item scoped through its parent review's school.
        """

        stmt = (
            self._item_query(
                include_relationships=include_relationships,
            )
            .join(
                AssessmentModerationReview,
                AssessmentModerationItem.review_id == AssessmentModerationReview.id,
            )
            .where(
                AssessmentModerationItem.id == item_id,
                AssessmentModerationReview.school_id == school_id,
            )
        )

        result = await self.db.execute(
            stmt,
        )

        return result.scalars().unique().one_or_none()

    async def get_item_for_response(
        self,
        review_id: int,
        response_id: int,
        *,
        include_relationships: bool = False,
    ) -> AssessmentModerationItem | None:
        """
        Return the moderation item for one response within one review.
        """

        stmt = self._item_query(
            include_relationships=include_relationships,
        ).where(
            AssessmentModerationItem.review_id == review_id,
            AssessmentModerationItem.response_id == response_id,
        )

        result = await self.db.execute(
            stmt,
        )

        return result.scalars().unique().one_or_none()

    async def list_items_for_review(
        self,
        review_id: int,
        *,
        include_relationships: bool = False,
    ) -> list[AssessmentModerationItem]:
        """
        Return all moderation items belonging to one review.
        """

        stmt = (
            self._item_query(
                include_relationships=include_relationships,
            )
            .where(
                AssessmentModerationItem.review_id == review_id,
            )
            .order_by(
                AssessmentModerationItem.id.asc(),
            )
        )

        result = await self.db.execute(
            stmt,
        )

        return list(
            result.scalars().unique().all(),
        )

    # ------------------------------------------------------------------
    # Item persistence
    # ------------------------------------------------------------------

    async def create_item(
        self,
        *,
        review_id: int,
        response_id: int,
        marking_decision_id: int,
        outcome: AssessmentModerationItemOutcome,
        reviewed_by_id: int,
        mark_before_snapshot: Decimal | None = None,
        mark_after_snapshot: Decimal | None = None,
        maximum_mark_snapshot: Decimal | None = None,
        mark_changed: bool = False,
        decision_status_before_snapshot: str | None = None,
        decision_status_after_snapshot: str | None = None,
        moderator_comment: str | None = None,
        evidence_notes: str | None = None,
    ) -> AssessmentModerationItem:
        """
        Create immutable moderation evidence for one reviewed response.

        A response may occur at most once in a given moderation review.

        The explicit duplicate lookup provides a clear repository error for
        normal callers. The database unique constraint remains necessary for
        concurrency safety.
        """

        existing = await self.get_item_for_response(
            review_id,
            response_id,
        )

        if existing is not None:
            raise ValueError(
                "This response has already been recorded in the moderation review.",
            )

        item = AssessmentModerationItem(
            review_id=review_id,
            response_id=response_id,
            marking_decision_id=marking_decision_id,
            outcome=outcome,
            mark_before_snapshot=mark_before_snapshot,
            mark_after_snapshot=mark_after_snapshot,
            maximum_mark_snapshot=maximum_mark_snapshot,
            mark_changed=mark_changed,
            decision_status_before_snapshot=(decision_status_before_snapshot),
            decision_status_after_snapshot=(decision_status_after_snapshot),
            moderator_comment=moderator_comment,
            evidence_notes=evidence_notes,
            reviewed_by_id=reviewed_by_id,
        )

        self.db.add(
            item,
        )

        await self.db.flush()
        await self.db.refresh(
            item,
        )

        return item

    async def save_item(
        self,
        item: AssessmentModerationItem,
    ) -> AssessmentModerationItem:
        """
        Flush an existing moderation item.

        Whether an item remains editable is a service-layer workflow rule.
        Completed moderation evidence should normally be treated as immutable.
        """

        self.db.add(
            item,
        )

        await self.db.flush()
        await self.db.refresh(
            item,
        )

        return item
