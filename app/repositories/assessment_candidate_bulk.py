from __future__ import annotations

from collections.abc import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_candidate import AssessmentCandidate


class AssessmentCandidateBulkRepository:
    """
    Repository primitives for bulk assessment-candidate allocation.

    This repository complements ``AssessmentCandidateRepository`` rather than
    replacing the existing single-candidate workflow.

    Responsibilities are deliberately narrow:

    - determine which students are already allocated to an assessment;
    - persist a validated batch of new candidate allocations efficiently.

    The repository never commits or rolls back transactions. Transaction
    ownership remains with the calling service.
    """

    _IN_CLAUSE_CHUNK_SIZE = 500

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Validation helpers
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

    @classmethod
    def _normalise_student_ids(
        cls,
        student_ids: Iterable[int],
    ) -> list[int]:
        """
        Validate, deduplicate and deterministically order student identifiers.

        Duplicate IDs in an input collection do not require duplicate database
        work, so they are intentionally collapsed here.
        """

        unique_ids: set[int] = set()

        for student_id in student_ids:
            cls._validate_positive_integer(
                student_id,
                "student_id",
            )

            unique_ids.add(
                student_id,
            )

        return sorted(
            unique_ids,
        )

    @classmethod
    def _chunks(
        cls,
        values: Sequence[int],
    ) -> Iterable[Sequence[int]]:
        """
        Yield safely sized chunks for SQL ``IN`` predicates.

        Keeping the chunk size conservative avoids backend parameter-limit
        problems when a large cohort is allocated.
        """

        for start in range(
            0,
            len(values),
            cls._IN_CLAUSE_CHUNK_SIZE,
        ):
            yield values[start : start + cls._IN_CLAUSE_CHUNK_SIZE]

    # ------------------------------------------------------------------
    # Existing allocation lookup
    # ------------------------------------------------------------------

    async def get_existing_student_ids(
        self,
        *,
        assessment_id: int,
        student_ids: Iterable[int],
    ) -> set[int]:
        """
        Return supplied student IDs already allocated to the assessment.

        The operation is performed in bounded set-based queries rather than one
        existence query per student.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        normalised_student_ids = self._normalise_student_ids(
            student_ids,
        )

        if not normalised_student_ids:
            return set()

        existing_student_ids: set[int] = set()

        for student_id_chunk in self._chunks(
            normalised_student_ids,
        ):
            result = await self.db.execute(
                select(
                    AssessmentCandidate.student_id,
                ).where(
                    AssessmentCandidate.assessment_id == assessment_id,
                    AssessmentCandidate.student_id.in_(
                        student_id_chunk,
                    ),
                ),
            )

            existing_student_ids.update(
                result.scalars().all(),
            )

        return existing_student_ids

    # ------------------------------------------------------------------
    # Bulk persistence
    # ------------------------------------------------------------------

    async def create_candidates(
        self,
        candidates: Sequence[AssessmentCandidate],
    ) -> list[AssessmentCandidate]:
        """
        Add and flush a batch of candidate allocations.

        All candidates in one call must belong to the same assessment and each
        student may appear only once in the supplied batch.

        Database uniqueness on ``(assessment_id, student_id)`` remains the
        final concurrency safeguard.

        This method does not commit the transaction.
        """

        if not candidates:
            return []

        assessment_ids: set[int] = set()
        student_ids: set[int] = set()

        for candidate in candidates:
            self._validate_positive_integer(
                candidate.assessment_id,
                "candidate.assessment_id",
            )
            self._validate_positive_integer(
                candidate.student_id,
                "candidate.student_id",
            )

            assessment_ids.add(
                candidate.assessment_id,
            )

            if candidate.student_id in student_ids:
                raise ValueError(
                    "Bulk candidate allocation contains a duplicate "
                    f"student_id: {candidate.student_id}.",
                )

            student_ids.add(
                candidate.student_id,
            )

        if len(assessment_ids) != 1:
            raise ValueError(
                "All candidates in one bulk allocation must belong to "
                "the same assessment.",
            )

        self.db.add_all(
            list(candidates),
        )

        await self.db.flush()

        candidate_ids = [
            candidate.id for candidate in candidates if candidate.id is not None
        ]

        if len(candidate_ids) != len(candidates):
            raise RuntimeError(
                "One or more bulk candidate allocations were not assigned "
                "database identifiers after flush.",
            )

        result = await self.db.execute(
            select(
                AssessmentCandidate,
            )
            .where(
                AssessmentCandidate.id.in_(
                    candidate_ids,
                ),
            )
            .order_by(
                AssessmentCandidate.id.asc(),
            ),
        )

        return list(
            result.scalars().unique().all(),
        )
