from __future__ import annotations

from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment_grading import (
    AssessmentGradeBoundary,
    AssessmentGradingBasis,
    AssessmentGradingScheme,
)


class AssessmentGradingRepository:
    """
    Repository for assessment grading schemes and grade boundaries.

    The repository provides persistence operations only.

    School access control, assessment ownership validation, grading rules,
    boundary validation and grade resolution belong in the service layer.

    Current model rules guarantee:

        - one grading scheme per assessment;
        - unique grade labels within a scheme;
        - unique minimum values within a scheme;
        - unique display orders within a scheme.

    Repository reads that return a grading scheme eagerly load its
    boundaries so callers receive a complete grading configuration.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Grading schemes
    # ------------------------------------------------------------------

    async def get_scheme_by_id(
        self,
        scheme_id: int,
    ) -> AssessmentGradingScheme | None:
        """Return one grading scheme with its boundaries."""

        stmt = (
            select(AssessmentGradingScheme)
            .options(
                selectinload(
                    AssessmentGradingScheme.boundaries,
                ),
            )
            .where(
                AssessmentGradingScheme.id == scheme_id,
            )
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_scheme_for_assessment(
        self,
        assessment_id: int,
    ) -> AssessmentGradingScheme | None:
        """Return the grading scheme configured for an assessment."""

        stmt = (
            select(AssessmentGradingScheme)
            .options(
                selectinload(
                    AssessmentGradingScheme.boundaries,
                ),
            )
            .where(
                AssessmentGradingScheme.assessment_id == assessment_id,
            )
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_scheme_for_assessment(
        self,
        assessment_id: int,
    ) -> AssessmentGradingScheme | None:
        """Return the active grading scheme for an assessment."""

        stmt = (
            select(AssessmentGradingScheme)
            .options(
                selectinload(
                    AssessmentGradingScheme.boundaries,
                ),
            )
            .where(
                AssessmentGradingScheme.assessment_id == assessment_id,
                AssessmentGradingScheme.is_active.is_(True),
            )
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_scheme(
        self,
        *,
        assessment_id: int,
        name: str,
        basis: AssessmentGradingBasis,
        created_by_id: int,
        description: str | None = None,
        is_active: bool = True,
    ) -> AssessmentGradingScheme:
        """Create and flush one assessment grading scheme."""

        scheme = AssessmentGradingScheme(
            assessment_id=assessment_id,
            name=name,
            description=description,
            basis=basis,
            is_active=is_active,
            created_by_id=created_by_id,
        )

        self.db.add(scheme)
        await self.db.flush()

        return scheme

    async def update_scheme(
        self,
        scheme: AssessmentGradingScheme,
        *,
        name: str | None = None,
        description: str | None = None,
        basis: AssessmentGradingBasis | None = None,
        is_active: bool | None = None,
    ) -> AssessmentGradingScheme:
        """
        Update supplied grading-scheme fields and flush the changes.

        ``None`` means that the corresponding field is left unchanged.
        Service-layer methods that need to explicitly clear nullable fields
        may assign them directly before calling ``flush``.
        """

        if name is not None:
            scheme.name = name

        if description is not None:
            scheme.description = description

        if basis is not None:
            scheme.basis = basis

        if is_active is not None:
            scheme.is_active = is_active

        await self.db.flush()
        return scheme

    async def delete_scheme(
        self,
        scheme: AssessmentGradingScheme,
    ) -> None:
        """Delete a grading scheme and its dependent boundaries."""

        await self.db.delete(scheme)
        await self.db.flush()

    # ------------------------------------------------------------------
    # Grade boundaries
    # ------------------------------------------------------------------

    async def get_boundary_by_id(
        self,
        boundary_id: int,
    ) -> AssessmentGradeBoundary | None:
        """Return one grade boundary."""

        stmt = select(AssessmentGradeBoundary).where(
            AssessmentGradeBoundary.id == boundary_id,
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_boundaries(
        self,
        grading_scheme_id: int,
    ) -> list[AssessmentGradeBoundary]:
        """
        Return all boundaries for a scheme in grading order.

        Highest threshold is returned first. ``order`` and ``id`` provide
        deterministic secondary ordering.
        """

        stmt = (
            select(AssessmentGradeBoundary)
            .where(
                AssessmentGradeBoundary.grading_scheme_id == grading_scheme_id,
            )
            .order_by(
                AssessmentGradeBoundary.minimum_value.desc(),
                AssessmentGradeBoundary.order.asc(),
                AssessmentGradeBoundary.id.asc(),
            )
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_boundary(
        self,
        *,
        grading_scheme_id: int,
        grade_label: str,
        minimum_value: Decimal,
        order: int,
        description: str | None = None,
        grade_points: Decimal | None = None,
        is_pass: bool | None = None,
    ) -> AssessmentGradeBoundary:
        """Create and flush one grade boundary."""

        boundary = AssessmentGradeBoundary(
            grading_scheme_id=grading_scheme_id,
            grade_label=grade_label,
            minimum_value=minimum_value,
            order=order,
            description=description,
            grade_points=grade_points,
            is_pass=is_pass,
        )

        self.db.add(boundary)
        await self.db.flush()

        return boundary

    async def update_boundary(
        self,
        boundary: AssessmentGradeBoundary,
        *,
        grade_label: str | None = None,
        minimum_value: Decimal | None = None,
        order: int | None = None,
        description: str | None = None,
        grade_points: Decimal | None = None,
        is_pass: bool | None = None,
    ) -> AssessmentGradeBoundary:
        """
        Update supplied boundary fields and flush the changes.

        ``None`` leaves a field unchanged. Nullable fields that must be
        explicitly cleared can be assigned directly by the service layer.
        """

        if grade_label is not None:
            boundary.grade_label = grade_label

        if minimum_value is not None:
            boundary.minimum_value = minimum_value

        if order is not None:
            boundary.order = order

        if description is not None:
            boundary.description = description

        if grade_points is not None:
            boundary.grade_points = grade_points

        if is_pass is not None:
            boundary.is_pass = is_pass

        await self.db.flush()
        return boundary

    async def delete_boundary(
        self,
        boundary: AssessmentGradeBoundary,
    ) -> None:
        """Delete one grade boundary."""

        await self.db.delete(boundary)
        await self.db.flush()

    async def delete_boundaries_for_scheme(
        self,
        grading_scheme_id: int,
    ) -> int:
        """
        Delete every boundary belonging to a grading scheme.

        Return the database-reported number of deleted rows.
        """

        stmt = delete(AssessmentGradeBoundary).where(
            AssessmentGradeBoundary.grading_scheme_id == grading_scheme_id,
        )

        result = await self.db.execute(stmt)
        await self.db.flush()

        return int(result.rowcount or 0)

    # ------------------------------------------------------------------
    # Boundary lookups
    # ------------------------------------------------------------------

    async def get_boundary_by_label(
        self,
        *,
        grading_scheme_id: int,
        grade_label: str,
    ) -> AssessmentGradeBoundary | None:
        """Return a boundary by its grade label."""

        stmt = select(AssessmentGradeBoundary).where(
            AssessmentGradeBoundary.grading_scheme_id == grading_scheme_id,
            AssessmentGradeBoundary.grade_label == grade_label,
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_boundary_by_minimum_value(
        self,
        *,
        grading_scheme_id: int,
        minimum_value: Decimal,
    ) -> AssessmentGradeBoundary | None:
        """Return a boundary by its inclusive minimum threshold."""

        stmt = select(AssessmentGradeBoundary).where(
            AssessmentGradeBoundary.grading_scheme_id == grading_scheme_id,
            AssessmentGradeBoundary.minimum_value == minimum_value,
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_boundary_by_order(
        self,
        *,
        grading_scheme_id: int,
        order: int,
    ) -> AssessmentGradeBoundary | None:
        """Return a boundary by its configured order."""

        stmt = select(AssessmentGradeBoundary).where(
            AssessmentGradeBoundary.grading_scheme_id == grading_scheme_id,
            AssessmentGradeBoundary.order == order,
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def resolve_boundary(
        self,
        *,
        grading_scheme_id: int,
        value: Decimal,
    ) -> AssessmentGradeBoundary | None:
        """
        Resolve a grading value to its highest matching boundary.

        Boundaries are inclusive. For example, with thresholds:

            9 >= 80
            8 >= 70
            7 >= 60

        a value of exactly 70 resolves to grade 8.

        If the value is below every configured threshold, ``None`` is
        returned. The service layer decides whether that means ungraded,
        incomplete configuration, or another application-level outcome.
        """

        stmt = (
            select(AssessmentGradeBoundary)
            .where(
                AssessmentGradeBoundary.grading_scheme_id == grading_scheme_id,
                AssessmentGradeBoundary.minimum_value <= value,
            )
            .order_by(
                AssessmentGradeBoundary.minimum_value.desc(),
                AssessmentGradeBoundary.order.asc(),
                AssessmentGradeBoundary.id.asc(),
            )
            .limit(1)
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    async def flush(self) -> None:
        """Flush pending grading changes."""

        await self.db.flush()

    async def refresh_scheme(
        self,
        scheme: AssessmentGradingScheme,
    ) -> AssessmentGradingScheme:
        """Refresh a grading scheme from the database."""

        await self.db.refresh(scheme)
        return scheme

    async def refresh_boundary(
        self,
        boundary: AssessmentGradeBoundary,
    ) -> AssessmentGradeBoundary:
        """Refresh a grade boundary from the database."""

        await self.db.refresh(boundary)
        return boundary
