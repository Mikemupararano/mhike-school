from __future__ import annotations

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment import Assessment
from app.models.assessment_candidate import (
    AssessmentCandidate,
    AssessmentCandidateStatus,
    AssessmentScript,
    AssessmentScriptStatus,
)


class AssessmentCandidateRepository:
    """
    Repository for assessment candidate allocations and submitted scripts.

    Candidate school scope is derived through the owning Assessment rather
    than duplicated on the candidate record.

    This repository never commits or rolls back transactions. Transaction
    ownership remains with the calling service, endpoint, background task,
    or other application workflow.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Validation and normalisation
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

    @staticmethod
    def _normalise_optional_text(
        value: str | None,
        *,
        field_name: str,
        max_length: int | None = None,
    ) -> str | None:
        """
        Return a trimmed optional text value.

        Blank strings are normalised to ``None``.
        """

        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError(
                f"{field_name} must be a string or None.",
            )

        cleaned = value.strip()

        if not cleaned:
            return None

        if max_length is not None and len(cleaned) > max_length:
            raise ValueError(
                f"{field_name} cannot exceed {max_length} characters.",
            )

        return cleaned

    @staticmethod
    def _normalise_candidate_status(
        value: AssessmentCandidateStatus | str,
    ) -> AssessmentCandidateStatus:
        """
        Return a valid AssessmentCandidateStatus value.
        """

        if isinstance(
            value,
            AssessmentCandidateStatus,
        ):
            return value

        if not isinstance(value, str):
            raise ValueError(
                "Candidate status must be an " "AssessmentCandidateStatus or string.",
            )

        try:
            return AssessmentCandidateStatus(
                value.strip(),
            )
        except ValueError as exc:
            raise ValueError(
                f"Invalid assessment candidate status: {value!r}.",
            ) from exc

    @staticmethod
    def _normalise_script_status(
        value: AssessmentScriptStatus | str,
    ) -> AssessmentScriptStatus:
        """
        Return a valid AssessmentScriptStatus value.
        """

        if isinstance(
            value,
            AssessmentScriptStatus,
        ):
            return value

        if not isinstance(value, str):
            raise ValueError(
                "Script status must be an AssessmentScriptStatus or string.",
            )

        try:
            return AssessmentScriptStatus(
                value.strip(),
            )
        except ValueError as exc:
            raise ValueError(
                f"Invalid assessment script status: {value!r}.",
            ) from exc

    # ------------------------------------------------------------------
    # Relationship loading
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_candidate_relationship_loading(
        statement,
        *,
        include_relationships: bool,
    ):
        """
        Apply standard candidate eager loading.

        Loaded relationships:

        - assessment;
        - student;
        - scripts.

        Script responses are intentionally not loaded here because those may
        grow large and belong to dedicated response/marking workflows.

        ``populate_existing=True`` prevents stale in-session script
        collections after new script versions are created.
        """

        if not include_relationships:
            return statement

        return statement.execution_options(
            populate_existing=True,
        ).options(
            selectinload(
                AssessmentCandidate.assessment,
            ),
            selectinload(
                AssessmentCandidate.student,
            ),
            selectinload(
                AssessmentCandidate.scripts,
            ),
        )

    @staticmethod
    def _apply_script_relationship_loading(
        statement,
        *,
        include_relationships: bool,
    ):
        """
        Apply standard script eager loading.

        Loaded relationships:

        - candidate;
        - candidate assessment;
        - candidate student.

        Question responses are intentionally excluded from the standard
        repository load path.
        """

        if not include_relationships:
            return statement

        return statement.execution_options(
            populate_existing=True,
        ).options(
            selectinload(
                AssessmentScript.candidate,
            ).selectinload(
                AssessmentCandidate.assessment,
            ),
            selectinload(
                AssessmentScript.candidate,
            ).selectinload(
                AssessmentCandidate.student,
            ),
        )

    # ------------------------------------------------------------------
    # Candidate lookup
    # ------------------------------------------------------------------

    async def get_candidate_by_id(
        self,
        candidate_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssessmentCandidate | None:
        """
        Return a candidate allocation by global identifier.
        """

        self._validate_positive_integer(
            candidate_id,
            "candidate_id",
        )

        statement = select(
            AssessmentCandidate,
        ).where(
            AssessmentCandidate.id == candidate_id,
        )

        statement = self._apply_candidate_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_candidate_by_id_and_school(
        self,
        candidate_id: int,
        school_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssessmentCandidate | None:
        """
        Return a candidate only when its assessment belongs to the school.
        """

        self._validate_positive_integer(
            candidate_id,
            "candidate_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = (
            select(
                AssessmentCandidate,
            )
            .join(
                Assessment,
                Assessment.id == AssessmentCandidate.assessment_id,
            )
            .where(
                AssessmentCandidate.id == candidate_id,
                Assessment.school_id == school_id,
            )
        )

        statement = self._apply_candidate_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_candidate_by_assessment_and_student(
        self,
        *,
        assessment_id: int,
        student_id: int,
        include_relationships: bool = True,
    ) -> AssessmentCandidate | None:
        """
        Return a student's allocation to one assessment.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )
        self._validate_positive_integer(
            student_id,
            "student_id",
        )

        statement = select(
            AssessmentCandidate,
        ).where(
            AssessmentCandidate.assessment_id == assessment_id,
            AssessmentCandidate.student_id == student_id,
        )

        statement = self._apply_candidate_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Candidate collections
    # ------------------------------------------------------------------

    async def list_candidates_by_assessment(
        self,
        assessment_id: int,
        *,
        status: AssessmentCandidateStatus | str | None = None,
        include_relationships: bool = True,
    ) -> list[AssessmentCandidate]:
        """
        Return candidates allocated to one assessment.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        statement = select(
            AssessmentCandidate,
        ).where(
            AssessmentCandidate.assessment_id == assessment_id,
        )

        if status is not None:
            normalised_status = self._normalise_candidate_status(
                status,
            )

            statement = statement.where(
                AssessmentCandidate.status == normalised_status,
            )

        statement = statement.order_by(
            AssessmentCandidate.id.asc(),
        )

        statement = self._apply_candidate_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().unique().all(),
        )

    async def list_candidates_by_assessment_and_school(
        self,
        *,
        assessment_id: int,
        school_id: int,
        status: AssessmentCandidateStatus | str | None = None,
        include_relationships: bool = True,
    ) -> list[AssessmentCandidate]:
        """
        Return candidates for an assessment within one school.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = (
            select(
                AssessmentCandidate,
            )
            .join(
                Assessment,
                Assessment.id == AssessmentCandidate.assessment_id,
            )
            .where(
                AssessmentCandidate.assessment_id == assessment_id,
                Assessment.school_id == school_id,
            )
        )

        if status is not None:
            normalised_status = self._normalise_candidate_status(
                status,
            )

            statement = statement.where(
                AssessmentCandidate.status == normalised_status,
            )

        statement = statement.order_by(
            AssessmentCandidate.id.asc(),
        )

        statement = self._apply_candidate_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().unique().all(),
        )

    async def list_candidates_by_student(
        self,
        student_id: int,
        *,
        school_id: int | None = None,
        status: AssessmentCandidateStatus | str | None = None,
        include_relationships: bool = True,
    ) -> list[AssessmentCandidate]:
        """
        Return assessment allocations for one student.

        When ``school_id`` is supplied, results are restricted through the
        owning assessment's school.
        """

        self._validate_positive_integer(
            student_id,
            "student_id",
        )

        statement = select(
            AssessmentCandidate,
        ).where(
            AssessmentCandidate.student_id == student_id,
        )

        if school_id is not None:
            self._validate_positive_integer(
                school_id,
                "school_id",
            )

            statement = statement.join(
                Assessment,
                Assessment.id == AssessmentCandidate.assessment_id,
            ).where(
                Assessment.school_id == school_id,
            )

        if status is not None:
            normalised_status = self._normalise_candidate_status(
                status,
            )

            statement = statement.where(
                AssessmentCandidate.status == normalised_status,
            )

        statement = statement.order_by(
            AssessmentCandidate.allocated_at.desc(),
            AssessmentCandidate.id.desc(),
        )

        statement = self._apply_candidate_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().unique().all(),
        )

    # ------------------------------------------------------------------
    # Candidate existence checks
    # ------------------------------------------------------------------

    async def candidate_exists(
        self,
        candidate_id: int,
    ) -> bool:
        """
        Return whether a candidate allocation exists.
        """

        self._validate_positive_integer(
            candidate_id,
            "candidate_id",
        )

        result = await self.db.execute(
            select(
                exists().where(
                    AssessmentCandidate.id == candidate_id,
                ),
            ),
        )

        return bool(
            result.scalar_one(),
        )

    async def allocation_exists(
        self,
        *,
        assessment_id: int,
        student_id: int,
    ) -> bool:
        """
        Return whether the student is already allocated to the assessment.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )
        self._validate_positive_integer(
            student_id,
            "student_id",
        )

        result = await self.db.execute(
            select(
                exists().where(
                    AssessmentCandidate.assessment_id == assessment_id,
                    AssessmentCandidate.student_id == student_id,
                ),
            ),
        )

        return bool(
            result.scalar_one(),
        )

    # ------------------------------------------------------------------
    # Candidate persistence
    # ------------------------------------------------------------------

    async def create_candidate(
        self,
        candidate: AssessmentCandidate,
    ) -> AssessmentCandidate:
        """
        Add and flush a new candidate allocation.

        This method does not commit the transaction.
        """

        self._validate_positive_integer(
            candidate.assessment_id,
            "assessment_id",
        )
        self._validate_positive_integer(
            candidate.student_id,
            "student_id",
        )

        candidate.status = self._normalise_candidate_status(
            candidate.status,
        )

        candidate.candidate_number = self._normalise_optional_text(
            candidate.candidate_number,
            field_name="candidate_number",
            max_length=100,
        )

        candidate.access_arrangements = self._normalise_optional_text(
            candidate.access_arrangements,
            field_name="access_arrangements",
        )

        self.db.add(
            candidate,
        )

        await self.db.flush()
        await self.db.refresh(
            candidate,
        )

        return candidate

    async def save_candidate(
        self,
        candidate: AssessmentCandidate,
    ) -> AssessmentCandidate:
        """
        Persist and flush an existing candidate allocation.

        This method does not commit the transaction.
        """

        if candidate.id is None:
            raise ValueError(
                "Cannot save a candidate without an ID.",
            )

        self._validate_positive_integer(
            candidate.id,
            "candidate.id",
        )
        self._validate_positive_integer(
            candidate.assessment_id,
            "assessment_id",
        )
        self._validate_positive_integer(
            candidate.student_id,
            "student_id",
        )

        candidate.status = self._normalise_candidate_status(
            candidate.status,
        )

        candidate.candidate_number = self._normalise_optional_text(
            candidate.candidate_number,
            field_name="candidate_number",
            max_length=100,
        )

        candidate.access_arrangements = self._normalise_optional_text(
            candidate.access_arrangements,
            field_name="access_arrangements",
        )

        self.db.add(
            candidate,
        )

        await self.db.flush()
        await self.db.refresh(
            candidate,
        )

        return candidate

    async def delete_candidate(
        self,
        candidate: AssessmentCandidate,
    ) -> None:
        """
        Delete and flush a candidate allocation.

        Database/ORM cascade rules remove subordinate scripts and responses.
        """

        if candidate.id is None:
            raise ValueError(
                "Cannot delete a candidate without an ID.",
            )

        self._validate_positive_integer(
            candidate.id,
            "candidate.id",
        )

        await self.db.delete(
            candidate,
        )

        await self.db.flush()

    # ------------------------------------------------------------------
    # Script lookup
    # ------------------------------------------------------------------

    async def get_script_by_id(
        self,
        script_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssessmentScript | None:
        """
        Return a script by global identifier.
        """

        self._validate_positive_integer(
            script_id,
            "script_id",
        )

        statement = select(
            AssessmentScript,
        ).where(
            AssessmentScript.id == script_id,
        )

        statement = self._apply_script_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_script_by_id_and_school(
        self,
        script_id: int,
        school_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssessmentScript | None:
        """
        Return a script only when its candidate's assessment is in the school.
        """

        self._validate_positive_integer(
            script_id,
            "script_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        statement = (
            select(
                AssessmentScript,
            )
            .join(
                AssessmentCandidate,
                AssessmentCandidate.id == AssessmentScript.candidate_id,
            )
            .join(
                Assessment,
                Assessment.id == AssessmentCandidate.assessment_id,
            )
            .where(
                AssessmentScript.id == script_id,
                Assessment.school_id == school_id,
            )
        )

        statement = self._apply_script_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_script_by_candidate_and_version(
        self,
        *,
        candidate_id: int,
        version: int,
        include_relationships: bool = True,
    ) -> AssessmentScript | None:
        """
        Return one script version for a candidate.
        """

        self._validate_positive_integer(
            candidate_id,
            "candidate_id",
        )
        self._validate_positive_integer(
            version,
            "version",
        )

        statement = select(
            AssessmentScript,
        ).where(
            AssessmentScript.candidate_id == candidate_id,
            AssessmentScript.version == version,
        )

        statement = self._apply_script_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_latest_script(
        self,
        candidate_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssessmentScript | None:
        """
        Return the highest-numbered script version for a candidate.
        """

        self._validate_positive_integer(
            candidate_id,
            "candidate_id",
        )

        statement = (
            select(
                AssessmentScript,
            )
            .where(
                AssessmentScript.candidate_id == candidate_id,
            )
            .order_by(
                AssessmentScript.version.desc(),
                AssessmentScript.id.desc(),
            )
            .limit(1)
        )

        statement = self._apply_script_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return result.scalar_one_or_none()

    async def get_next_script_version(
        self,
        candidate_id: int,
    ) -> int:
        """
        Return the next available script version number for a candidate.
        """

        self._validate_positive_integer(
            candidate_id,
            "candidate_id",
        )

        result = await self.db.execute(
            select(
                func.max(
                    AssessmentScript.version,
                ),
            ).where(
                AssessmentScript.candidate_id == candidate_id,
            ),
        )

        current_maximum = result.scalar_one_or_none()

        if current_maximum is None:
            return 1

        return int(current_maximum) + 1

    # ------------------------------------------------------------------
    # Script collections
    # ------------------------------------------------------------------

    async def list_scripts_by_candidate(
        self,
        candidate_id: int,
        *,
        status: AssessmentScriptStatus | str | None = None,
        include_relationships: bool = True,
    ) -> list[AssessmentScript]:
        """
        Return all script versions for a candidate.
        """

        self._validate_positive_integer(
            candidate_id,
            "candidate_id",
        )

        statement = select(
            AssessmentScript,
        ).where(
            AssessmentScript.candidate_id == candidate_id,
        )

        if status is not None:
            normalised_status = self._normalise_script_status(
                status,
            )

            statement = statement.where(
                AssessmentScript.status == normalised_status,
            )

        statement = statement.order_by(
            AssessmentScript.version.asc(),
            AssessmentScript.id.asc(),
        )

        statement = self._apply_script_relationship_loading(
            statement,
            include_relationships=include_relationships,
        )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().unique().all(),
        )

    # ------------------------------------------------------------------
    # Script persistence
    # ------------------------------------------------------------------

    async def create_script(
        self,
        script: AssessmentScript,
    ) -> AssessmentScript:
        """
        Add and flush a new script version.

        This method does not automatically choose a version number and does
        not commit the transaction. Version allocation belongs to the service
        workflow so concurrent creation can be handled deliberately there.
        """

        self._validate_positive_integer(
            script.candidate_id,
            "candidate_id",
        )
        self._validate_positive_integer(
            script.version,
            "version",
        )

        script.status = self._normalise_script_status(
            script.status,
        )

        script.source_type = self._normalise_optional_text(
            script.source_type,
            field_name="source_type",
            max_length=100,
        )

        script.source_filename = self._normalise_optional_text(
            script.source_filename,
            field_name="source_filename",
            max_length=500,
        )

        script.storage_key = self._normalise_optional_text(
            script.storage_key,
            field_name="storage_key",
            max_length=1000,
        )

        script.mime_type = self._normalise_optional_text(
            script.mime_type,
            field_name="mime_type",
            max_length=255,
        )

        script.checksum = self._normalise_optional_text(
            script.checksum,
            field_name="checksum",
            max_length=255,
        )

        self.db.add(
            script,
        )

        await self.db.flush()
        await self.db.refresh(
            script,
        )

        return script

    async def save_script(
        self,
        script: AssessmentScript,
    ) -> AssessmentScript:
        """
        Persist and flush an existing script.

        This method does not commit the transaction.
        """

        if script.id is None:
            raise ValueError(
                "Cannot save a script without an ID.",
            )

        self._validate_positive_integer(
            script.id,
            "script.id",
        )
        self._validate_positive_integer(
            script.candidate_id,
            "candidate_id",
        )
        self._validate_positive_integer(
            script.version,
            "version",
        )

        script.status = self._normalise_script_status(
            script.status,
        )

        script.source_type = self._normalise_optional_text(
            script.source_type,
            field_name="source_type",
            max_length=100,
        )

        script.source_filename = self._normalise_optional_text(
            script.source_filename,
            field_name="source_filename",
            max_length=500,
        )

        script.storage_key = self._normalise_optional_text(
            script.storage_key,
            field_name="storage_key",
            max_length=1000,
        )

        script.mime_type = self._normalise_optional_text(
            script.mime_type,
            field_name="mime_type",
            max_length=255,
        )

        script.checksum = self._normalise_optional_text(
            script.checksum,
            field_name="checksum",
            max_length=255,
        )

        self.db.add(
            script,
        )

        await self.db.flush()
        await self.db.refresh(
            script,
        )

        return script

    async def delete_script(
        self,
        script: AssessmentScript,
    ) -> None:
        """
        Delete and flush a script version.
        """

        if script.id is None:
            raise ValueError(
                "Cannot delete a script without an ID.",
            )

        self._validate_positive_integer(
            script.id,
            "script.id",
        )

        await self.db.delete(
            script,
        )

        await self.db.flush()
