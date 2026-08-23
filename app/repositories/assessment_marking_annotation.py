from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment_marking_annotation import (
    AssessmentMarkingAnnotation,
)


class AssessmentMarkingAnnotationRepository:
    """
    Repository for examiner annotations placed on assessment responses.

    The repository performs persistence and lookup only. School scope,
    marker permissions, annotation geometry validation, palette validation,
    optimistic revision checks, and lifecycle rules belong to the service
    layer.

    The repository never commits or rolls back transactions.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_positive_integer(
        value: int,
        field_name: str,
    ) -> None:
        """
        Require a positive integer identifier.
        """

        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(
                f"{field_name} must be a positive integer.",
            )

    # ------------------------------------------------------------------
    # Relationship loading
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_relationship_loading(
        statement,
        *,
        include_relationships: bool,
    ):
        """
        Apply the standard eager-loading configuration.
        """

        if not include_relationships:
            return statement

        return statement.options(
            selectinload(
                AssessmentMarkingAnnotation.response,
            ),
            selectinload(
                AssessmentMarkingAnnotation.marker,
            ),
            selectinload(
                AssessmentMarkingAnnotation.palette_tool,
            ),
            selectinload(
                AssessmentMarkingAnnotation.deleted_by,
            ),
        )

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    async def get_by_id(
        self,
        annotation_id: int,
        *,
        include_relationships: bool = True,
        include_deleted: bool = False,
    ) -> AssessmentMarkingAnnotation | None:
        """
        Return one annotation by identifier.

        Deleted annotations are excluded unless ``include_deleted`` is True.
        """

        self._validate_positive_integer(
            annotation_id,
            "annotation_id",
        )

        statement = select(
            AssessmentMarkingAnnotation,
        ).where(
            AssessmentMarkingAnnotation.id == annotation_id,
        )

        if not include_deleted:
            statement = statement.where(
                AssessmentMarkingAnnotation.deleted_at.is_(None),
            )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        if include_relationships:
            statement = statement.execution_options(
                populate_existing=True,
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_by_id_and_response(
        self,
        annotation_id: int,
        response_id: int,
        *,
        include_relationships: bool = True,
        include_deleted: bool = False,
    ) -> AssessmentMarkingAnnotation | None:
        """
        Return one annotation only when it belongs to the supplied response.
        """

        self._validate_positive_integer(
            annotation_id,
            "annotation_id",
        )
        self._validate_positive_integer(
            response_id,
            "response_id",
        )

        statement = select(
            AssessmentMarkingAnnotation,
        ).where(
            AssessmentMarkingAnnotation.id == annotation_id,
            AssessmentMarkingAnnotation.response_id == response_id,
        )

        if not include_deleted:
            statement = statement.where(
                AssessmentMarkingAnnotation.deleted_at.is_(None),
            )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        if include_relationships:
            statement = statement.execution_options(
                populate_existing=True,
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def list_for_response(
        self,
        response_id: int,
        *,
        include_deleted: bool = False,
        include_relationships: bool = True,
    ) -> list[AssessmentMarkingAnnotation]:
        """
        Return annotations for one response in stable creation order.
        """

        self._validate_positive_integer(
            response_id,
            "response_id",
        )

        statement = select(
            AssessmentMarkingAnnotation,
        ).where(
            AssessmentMarkingAnnotation.response_id == response_id,
        )

        if not include_deleted:
            statement = statement.where(
                AssessmentMarkingAnnotation.deleted_at.is_(None),
            )

        statement = statement.order_by(
            AssessmentMarkingAnnotation.id.asc(),
        )

        statement = self._apply_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        if include_relationships:
            statement = statement.execution_options(
                populate_existing=True,
            )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().all(),
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def create(
        self,
        annotation: AssessmentMarkingAnnotation,
    ) -> AssessmentMarkingAnnotation:
        """
        Add one annotation to the current transaction.
        """

        self.db.add(
            annotation,
        )

        await self.db.flush()

        return annotation

    async def save(
        self,
        annotation: AssessmentMarkingAnnotation,
    ) -> AssessmentMarkingAnnotation:
        """
        Flush changes to an annotation.

        Revision management belongs to the service layer.
        """

        self.db.add(
            annotation,
        )

        await self.db.flush()

        return annotation

    async def update_if_revision(
        self,
        annotation_id: int,
        expected_revision: int,
        *,
        values: dict,
    ) -> bool:
        """
        Atomically update an active annotation when its revision still matches.

        Returns True when exactly one annotation was updated. A False result
        means the annotation was deleted, did not exist, or another request
        changed it first.

        The caller supplies only validated mutable values. Revision is always
        incremented here so optimistic concurrency cannot be bypassed.
        """

        self._validate_positive_integer(
            annotation_id,
            "annotation_id",
        )
        self._validate_positive_integer(
            expected_revision,
            "expected_revision",
        )

        safe_values = dict(
            values,
        )

        safe_values.pop(
            "id",
            None,
        )
        safe_values.pop(
            "response_id",
            None,
        )
        safe_values.pop(
            "marker_id",
            None,
        )
        safe_values.pop(
            "created_at",
            None,
        )
        safe_values.pop(
            "revision",
            None,
        )
        safe_values.pop(
            "deleted_at",
            None,
        )
        safe_values.pop(
            "deleted_by_id",
            None,
        )

        safe_values["revision"] = expected_revision + 1

        statement = (
            update(
                AssessmentMarkingAnnotation,
            )
            .where(
                AssessmentMarkingAnnotation.id == annotation_id,
                AssessmentMarkingAnnotation.revision == expected_revision,
                AssessmentMarkingAnnotation.deleted_at.is_(None),
            )
            .values(
                **safe_values,
            )
            .returning(
                AssessmentMarkingAnnotation.id,
            )
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none() is not None

    async def soft_delete_if_revision(
        self,
        annotation_id: int,
        expected_revision: int,
        *,
        deleted_at,
        deleted_by_id: int,
    ) -> bool:
        """
        Atomically soft-delete an active annotation at the expected revision.

        Soft deletion preserves examiner history and increments the revision.
        """

        self._validate_positive_integer(
            annotation_id,
            "annotation_id",
        )
        self._validate_positive_integer(
            expected_revision,
            "expected_revision",
        )
        self._validate_positive_integer(
            deleted_by_id,
            "deleted_by_id",
        )

        statement = (
            update(
                AssessmentMarkingAnnotation,
            )
            .where(
                AssessmentMarkingAnnotation.id == annotation_id,
                AssessmentMarkingAnnotation.revision == expected_revision,
                AssessmentMarkingAnnotation.deleted_at.is_(None),
            )
            .values(
                deleted_at=deleted_at,
                deleted_by_id=deleted_by_id,
                revision=expected_revision + 1,
            )
            .returning(
                AssessmentMarkingAnnotation.id,
            )
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none() is not None

    async def refresh(
        self,
        annotation: AssessmentMarkingAnnotation,
    ) -> AssessmentMarkingAnnotation:
        """
        Refresh one annotation from the database.
        """

        await self.db.refresh(
            annotation,
        )

        return annotation
