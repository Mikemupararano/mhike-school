from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment_result_outcome import (
    AssessmentResultChangeType,
    AssessmentResultOutcome,
    AssessmentResultOutcomeStatus,
)

_UNSET = object()


class AssessmentResultOutcomeRepository:
    """
    Persistence layer for authoritative assessment-result history.

    The repository deliberately does not commit or roll back transactions.
    Transaction ownership remains with the service layer.

    Core guarantees supported here:

        - candidate result history is versioned;
        - historical rows are never overwritten;
        - only one outcome may be authoritative per candidate;
        - superseded outcomes remain queryable indefinitely;
        - version sequencing is deterministic;
        - the current authoritative outcome can be resolved efficiently.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Validation / normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_positive_integer(
        value: int,
        *,
        field_name: str,
    ) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(
                f"{field_name} must be a positive integer.",
            )

        return value

    @staticmethod
    def _normalise_optional_text(
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        cleaned = str(
            value,
        ).strip()

        return cleaned or None

    @staticmethod
    def _normalise_decimal(
        value: Decimal | int | float | str,
        *,
        field_name: str,
    ) -> Decimal:
        try:
            decimal_value = Decimal(
                str(value),
            )
        except Exception as exc:
            raise ValueError(
                f"{field_name} must be numeric.",
            ) from exc

        if not decimal_value.is_finite():
            raise ValueError(
                f"{field_name} must be finite.",
            )

        return decimal_value

    @staticmethod
    def _normalise_optional_decimal(
        value: Decimal | int | float | str | None,
        *,
        field_name: str,
    ) -> Decimal | None:
        if value is None:
            return None

        return AssessmentResultOutcomeRepository._normalise_decimal(
            value,
            field_name=field_name,
        )

    @staticmethod
    def _normalise_status(
        value: AssessmentResultOutcomeStatus | str,
    ) -> AssessmentResultOutcomeStatus:
        if isinstance(
            value,
            AssessmentResultOutcomeStatus,
        ):
            return value

        try:
            return AssessmentResultOutcomeStatus(
                str(value).strip(),
            )
        except ValueError as exc:
            raise ValueError(
                "Invalid assessment result outcome status.",
            ) from exc

    @staticmethod
    def _normalise_change_type(
        value: AssessmentResultChangeType | str,
    ) -> AssessmentResultChangeType:
        if isinstance(
            value,
            AssessmentResultChangeType,
        ):
            return value

        try:
            return AssessmentResultChangeType(
                str(value).strip(),
            )
        except ValueError as exc:
            raise ValueError(
                "Invalid assessment result change type.",
            ) from exc

    @staticmethod
    def _normalise_bool(
        value: bool,
        *,
        field_name: str,
    ) -> bool:
        if not isinstance(value, bool):
            raise ValueError(
                f"{field_name} must be a boolean.",
            )

        return value

    # ------------------------------------------------------------------
    # Relationship loading
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_relationship_loading(
        statement,
    ):
        return statement.options(
            selectinload(
                AssessmentResultOutcome.assessment,
            ),
            selectinload(
                AssessmentResultOutcome.candidate,
            ),
            selectinload(
                AssessmentResultOutcome.script,
            ),
            selectinload(
                AssessmentResultOutcome.recorded_by,
            ),
            selectinload(
                AssessmentResultOutcome.withdrawn_by,
            ),
            selectinload(
                AssessmentResultOutcome.supersedes,
            ),
        )

    # ------------------------------------------------------------------
    # Primary lookups
    # ------------------------------------------------------------------

    async def get_by_id(
        self,
        outcome_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssessmentResultOutcome | None:
        self._validate_positive_integer(
            outcome_id,
            field_name="outcome_id",
        )

        statement = select(
            AssessmentResultOutcome,
        ).where(
            AssessmentResultOutcome.id == outcome_id,
        )

        if include_relationships:
            statement = self._apply_relationship_loading(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_by_id_and_school(
        self,
        outcome_id: int,
        school_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssessmentResultOutcome | None:
        self._validate_positive_integer(
            outcome_id,
            field_name="outcome_id",
        )
        self._validate_positive_integer(
            school_id,
            field_name="school_id",
        )

        statement = select(
            AssessmentResultOutcome,
        ).where(
            AssessmentResultOutcome.id == outcome_id,
            AssessmentResultOutcome.school_id == school_id,
        )

        if include_relationships:
            statement = self._apply_relationship_loading(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_authoritative_for_candidate(
        self,
        candidate_id: int,
        *,
        school_id: int | None = None,
        include_relationships: bool = True,
        for_update: bool = False,
    ) -> AssessmentResultOutcome | None:
        """
        Return the candidate's current authoritative outcome.

        ``for_update=True`` may be used by service-layer mutations when the
        current authoritative row needs to be superseded transactionally.
        """

        self._validate_positive_integer(
            candidate_id,
            field_name="candidate_id",
        )

        statement = select(
            AssessmentResultOutcome,
        ).where(
            AssessmentResultOutcome.candidate_id == candidate_id,
            AssessmentResultOutcome.is_authoritative.is_(True),
            AssessmentResultOutcome.status
            == AssessmentResultOutcomeStatus.AUTHORITATIVE,
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                field_name="school_id",
            )

            statement = statement.where(
                AssessmentResultOutcome.school_id == school_id,
            )

        if include_relationships:
            statement = self._apply_relationship_loading(
                statement,
            )

        if for_update:
            statement = statement.with_for_update()

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_latest_for_candidate(
        self,
        candidate_id: int,
        *,
        school_id: int | None = None,
        include_relationships: bool = True,
    ) -> AssessmentResultOutcome | None:
        self._validate_positive_integer(
            candidate_id,
            field_name="candidate_id",
        )

        statement = (
            select(
                AssessmentResultOutcome,
            )
            .where(
                AssessmentResultOutcome.candidate_id == candidate_id,
            )
            .order_by(
                AssessmentResultOutcome.version.desc(),
                AssessmentResultOutcome.id.desc(),
            )
            .limit(1)
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                field_name="school_id",
            )

            statement = statement.where(
                AssessmentResultOutcome.school_id == school_id,
            )

        if include_relationships:
            statement = self._apply_relationship_loading(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def list_for_candidate(
        self,
        candidate_id: int,
        *,
        school_id: int | None = None,
        include_relationships: bool = True,
    ) -> list[AssessmentResultOutcome]:
        """
        Return complete candidate outcome history from oldest to newest.
        """

        self._validate_positive_integer(
            candidate_id,
            field_name="candidate_id",
        )

        statement = select(
            AssessmentResultOutcome,
        ).where(
            AssessmentResultOutcome.candidate_id == candidate_id,
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                field_name="school_id",
            )

            statement = statement.where(
                AssessmentResultOutcome.school_id == school_id,
            )

        statement = statement.order_by(
            AssessmentResultOutcome.version.asc(),
            AssessmentResultOutcome.id.asc(),
        )

        if include_relationships:
            statement = self._apply_relationship_loading(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().all(),
        )

    async def list_for_assessment(
        self,
        assessment_id: int,
        *,
        school_id: int | None = None,
        authoritative_only: bool = False,
        include_relationships: bool = True,
    ) -> list[AssessmentResultOutcome]:
        self._validate_positive_integer(
            assessment_id,
            field_name="assessment_id",
        )

        statement = select(
            AssessmentResultOutcome,
        ).where(
            AssessmentResultOutcome.assessment_id == assessment_id,
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                field_name="school_id",
            )

            statement = statement.where(
                AssessmentResultOutcome.school_id == school_id,
            )

        if authoritative_only:
            statement = statement.where(
                AssessmentResultOutcome.is_authoritative.is_(True),
                AssessmentResultOutcome.status
                == AssessmentResultOutcomeStatus.AUTHORITATIVE,
            )

        statement = statement.order_by(
            AssessmentResultOutcome.candidate_id.asc(),
            AssessmentResultOutcome.version.asc(),
            AssessmentResultOutcome.id.asc(),
        )

        if include_relationships:
            statement = self._apply_relationship_loading(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().all(),
        )

    async def list_for_script(
        self,
        script_id: int,
        *,
        school_id: int | None = None,
        include_relationships: bool = True,
    ) -> list[AssessmentResultOutcome]:
        self._validate_positive_integer(
            script_id,
            field_name="script_id",
        )

        statement = select(
            AssessmentResultOutcome,
        ).where(
            AssessmentResultOutcome.script_id == script_id,
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                field_name="school_id",
            )

            statement = statement.where(
                AssessmentResultOutcome.school_id == school_id,
            )

        statement = statement.order_by(
            AssessmentResultOutcome.version.asc(),
            AssessmentResultOutcome.id.asc(),
        )

        if include_relationships:
            statement = self._apply_relationship_loading(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().all(),
        )

    # ------------------------------------------------------------------
    # Version sequencing
    # ------------------------------------------------------------------

    async def get_next_version(
        self,
        candidate_id: int,
        *,
        lock_history: bool = False,
    ) -> int:
        """
        Return the next candidate outcome version.

        PostgreSQL uniqueness still provides the final race-condition guard.

        ``lock_history=True`` may be used by the service when it wants to lock
        existing history before creating another version.
        """

        self._validate_positive_integer(
            candidate_id,
            field_name="candidate_id",
        )

        if lock_history:
            lock_statement = (
                select(
                    AssessmentResultOutcome.id,
                )
                .where(
                    AssessmentResultOutcome.candidate_id == candidate_id,
                )
                .order_by(
                    AssessmentResultOutcome.version.asc(),
                )
                .with_for_update()
            )

            await self.db.execute(
                lock_statement,
            )

        statement = select(
            func.max(
                AssessmentResultOutcome.version,
            ),
        ).where(
            AssessmentResultOutcome.candidate_id == candidate_id,
        )

        result = await self.db.execute(
            statement,
        )

        current_max = result.scalar_one_or_none()

        if current_max is None:
            return 1

        return (
            int(
                current_max,
            )
            + 1
        )

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    async def create_outcome(
        self,
        *,
        school_id: int,
        assessment_id: int,
        candidate_id: int,
        script_id: int,
        version: int,
        change_type: AssessmentResultChangeType | str,
        mark_awarded_snapshot: Decimal | int | float | str,
        maximum_mark_snapshot: Decimal | int | float | str,
        percentage_snapshot: Decimal | int | float | str | None,
        script_version_snapshot: int,
        effective_at: datetime,
        recorded_by_id: int,
        status: AssessmentResultOutcomeStatus | str = (
            AssessmentResultOutcomeStatus.DRAFT
        ),
        supersedes_id: int | None = None,
        is_authoritative: bool = False,
        grading_scheme_id_snapshot: int | None = None,
        grading_scheme_name_snapshot: str | None = None,
        grading_basis_snapshot: str | None = None,
        grade_boundary_id_snapshot: int | None = None,
        grade_label_snapshot: str | None = None,
        grade_points_snapshot: Decimal | int | float | str | None = None,
        is_pass_snapshot: bool | None = None,
        reason: str | None = None,
        notes: str | None = None,
    ) -> AssessmentResultOutcome:
        self._validate_positive_integer(
            school_id,
            field_name="school_id",
        )
        self._validate_positive_integer(
            assessment_id,
            field_name="assessment_id",
        )
        self._validate_positive_integer(
            candidate_id,
            field_name="candidate_id",
        )
        self._validate_positive_integer(
            script_id,
            field_name="script_id",
        )
        self._validate_positive_integer(
            version,
            field_name="version",
        )
        self._validate_positive_integer(
            script_version_snapshot,
            field_name="script_version_snapshot",
        )
        self._validate_positive_integer(
            recorded_by_id,
            field_name="recorded_by_id",
        )

        if supersedes_id is not None:
            self._validate_positive_integer(
                supersedes_id,
                field_name="supersedes_id",
            )

        if grading_scheme_id_snapshot is not None:
            self._validate_positive_integer(
                grading_scheme_id_snapshot,
                field_name="grading_scheme_id_snapshot",
            )

        if grade_boundary_id_snapshot is not None:
            self._validate_positive_integer(
                grade_boundary_id_snapshot,
                field_name="grade_boundary_id_snapshot",
            )

        if not isinstance(
            effective_at,
            datetime,
        ):
            raise ValueError(
                "effective_at must be a datetime.",
            )

        clean_status = self._normalise_status(
            status,
        )

        clean_change_type = self._normalise_change_type(
            change_type,
        )

        clean_is_authoritative = self._normalise_bool(
            is_authoritative,
            field_name="is_authoritative",
        )

        mark_awarded = self._normalise_decimal(
            mark_awarded_snapshot,
            field_name="mark_awarded_snapshot",
        )

        maximum_mark = self._normalise_decimal(
            maximum_mark_snapshot,
            field_name="maximum_mark_snapshot",
        )

        percentage = self._normalise_optional_decimal(
            percentage_snapshot,
            field_name="percentage_snapshot",
        )

        grade_points = self._normalise_optional_decimal(
            grade_points_snapshot,
            field_name="grade_points_snapshot",
        )

        if mark_awarded < Decimal("0"):
            raise ValueError(
                "mark_awarded_snapshot cannot be negative.",
            )

        if maximum_mark < Decimal("0"):
            raise ValueError(
                "maximum_mark_snapshot cannot be negative.",
            )

        if percentage is not None and (
            percentage < Decimal("0") or percentage > Decimal("100")
        ):
            raise ValueError(
                "percentage_snapshot must be between 0 and 100.",
            )

        if grade_points is not None and grade_points < Decimal("0"):
            raise ValueError(
                "grade_points_snapshot cannot be negative.",
            )

        if is_pass_snapshot is not None and not isinstance(
            is_pass_snapshot,
            bool,
        ):
            raise ValueError(
                "is_pass_snapshot must be a boolean or null.",
            )

        if (
            clean_is_authoritative
            and clean_status != AssessmentResultOutcomeStatus.AUTHORITATIVE
        ):
            raise ValueError(
                ("An authoritative outcome must have " "status='authoritative'."),
            )

        if (
            clean_status == AssessmentResultOutcomeStatus.AUTHORITATIVE
            and not clean_is_authoritative
        ):
            raise ValueError(
                (
                    "An outcome with status='authoritative' must set "
                    "is_authoritative=True."
                ),
            )

        outcome = AssessmentResultOutcome(
            school_id=school_id,
            assessment_id=assessment_id,
            candidate_id=candidate_id,
            script_id=script_id,
            version=version,
            status=clean_status,
            change_type=clean_change_type,
            supersedes_id=supersedes_id,
            is_authoritative=clean_is_authoritative,
            mark_awarded_snapshot=mark_awarded,
            maximum_mark_snapshot=maximum_mark,
            percentage_snapshot=percentage,
            grading_scheme_id_snapshot=grading_scheme_id_snapshot,
            grading_scheme_name_snapshot=self._normalise_optional_text(
                grading_scheme_name_snapshot,
            ),
            grading_basis_snapshot=self._normalise_optional_text(
                grading_basis_snapshot,
            ),
            grade_boundary_id_snapshot=grade_boundary_id_snapshot,
            grade_label_snapshot=self._normalise_optional_text(
                grade_label_snapshot,
            ),
            grade_points_snapshot=grade_points,
            is_pass_snapshot=is_pass_snapshot,
            script_version_snapshot=script_version_snapshot,
            reason=self._normalise_optional_text(
                reason,
            ),
            notes=self._normalise_optional_text(
                notes,
            ),
            effective_at=effective_at,
            recorded_by_id=recorded_by_id,
        )

        self.db.add(
            outcome,
        )

        return outcome

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    async def supersede_outcome(
        self,
        outcome: AssessmentResultOutcome,
    ) -> AssessmentResultOutcome:
        """
        Mark a previously authoritative row as superseded.

        Snapshot values remain untouched.
        """

        outcome.status = AssessmentResultOutcomeStatus.SUPERSEDED
        outcome.is_authoritative = False

        await self.db.flush()

        return outcome

    async def make_authoritative(
        self,
        outcome: AssessmentResultOutcome,
    ) -> AssessmentResultOutcome:
        """
        Mark an existing draft outcome as authoritative.

        The service layer must first supersede any existing authoritative row.
        The partial unique index provides the final database-level safeguard.
        """

        if outcome.status == AssessmentResultOutcomeStatus.WITHDRAWN:
            raise ValueError(
                "A withdrawn outcome cannot become authoritative.",
            )

        outcome.status = AssessmentResultOutcomeStatus.AUTHORITATIVE
        outcome.is_authoritative = True

        await self.db.flush()

        return outcome

    async def withdraw_outcome(
        self,
        outcome: AssessmentResultOutcome,
        *,
        withdrawn_at: datetime,
        withdrawn_by_id: int,
        withdrawal_reason: str,
    ) -> AssessmentResultOutcome:
        """
        Withdraw an outcome while preserving its complete snapshot.
        """

        if not isinstance(
            withdrawn_at,
            datetime,
        ):
            raise ValueError(
                "withdrawn_at must be a datetime.",
            )

        self._validate_positive_integer(
            withdrawn_by_id,
            field_name="withdrawn_by_id",
        )

        clean_reason = self._normalise_optional_text(
            withdrawal_reason,
        )

        if clean_reason is None:
            raise ValueError(
                "withdrawal_reason cannot be blank.",
            )

        outcome.status = AssessmentResultOutcomeStatus.WITHDRAWN
        outcome.is_authoritative = False
        outcome.withdrawn_at = withdrawn_at
        outcome.withdrawn_by_id = withdrawn_by_id
        outcome.withdrawal_reason = clean_reason

        await self.db.flush()

        return outcome

    # ------------------------------------------------------------------
    # Restricted metadata update
    # ------------------------------------------------------------------

    async def update_draft_metadata(
        self,
        outcome: AssessmentResultOutcome,
        *,
        reason: str | None | object = _UNSET,
        notes: str | None | object = _UNSET,
        effective_at: datetime | object = _UNSET,
    ) -> AssessmentResultOutcome:
        """
        Update non-result metadata on a DRAFT outcome only.

        Snapshot values themselves are intentionally not mutable here.
        """

        if outcome.status != AssessmentResultOutcomeStatus.DRAFT:
            raise ValueError(
                "Only draft outcomes may be updated.",
            )

        if reason is not _UNSET:
            outcome.reason = self._normalise_optional_text(
                reason,
            )

        if notes is not _UNSET:
            outcome.notes = self._normalise_optional_text(
                notes,
            )

        if effective_at is not _UNSET:
            if not isinstance(
                effective_at,
                datetime,
            ):
                raise ValueError(
                    "effective_at must be a datetime.",
                )

            outcome.effective_at = effective_at

        await self.db.flush()

        return outcome

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    async def delete_draft(
        self,
        outcome: AssessmentResultOutcome,
    ) -> None:
        """
        Delete a draft outcome that has never become authoritative.

        Historical official outcomes must not be deleted.
        """

        if outcome.status != AssessmentResultOutcomeStatus.DRAFT:
            raise ValueError(
                "Only draft assessment result outcomes may be deleted.",
            )

        await self.db.delete(
            outcome,
        )

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    async def flush(
        self,
    ) -> None:
        await self.db.flush()

    async def refresh(
        self,
        outcome: AssessmentResultOutcome,
    ) -> None:
        await self.db.refresh(
            outcome,
        )
