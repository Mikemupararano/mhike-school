from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment_question_extraction import (
    AssessmentQuestionExtraction,
    AssessmentQuestionExtractionStatus,
)


class AssessmentQuestionExtractionRepository:
    """
    Repository for assessment question-paper extraction attempts.

    Transaction ownership remains with the calling service. Repository
    methods may flush changes where needed, but they do not commit or roll
    back transactions.

    Extraction attempts are versioned and retained. A new extraction for the
    same source document receives the next version number rather than
    overwriting previous attempts.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

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
    def _normalise_status(
        status: AssessmentQuestionExtractionStatus | str,
    ) -> str:
        """
        Return a validated extraction status value.
        """

        if isinstance(
            status,
            AssessmentQuestionExtractionStatus,
        ):
            return status.value

        raw_status = (
            str(
                status,
            )
            .strip()
            .lower()
        )

        try:
            return AssessmentQuestionExtractionStatus(
                raw_status,
            ).value
        except ValueError as exc:
            valid_values = ", ".join(
                item.value for item in AssessmentQuestionExtractionStatus
            )
            raise ValueError(
                f"Invalid extraction status. Expected one of: {valid_values}.",
            ) from exc

    @staticmethod
    def _with_relationships(
        statement,
    ):
        """
        Apply standard eager loading for extraction records.
        """

        return statement.options(
            selectinload(
                AssessmentQuestionExtraction.assessment,
            ),
            selectinload(
                AssessmentQuestionExtraction.assessment_document,
            ),
            selectinload(
                AssessmentQuestionExtraction.requested_by,
            ),
            selectinload(
                AssessmentQuestionExtraction.imported_by,
            ),
        )

    async def get_by_id(
        self,
        extraction_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssessmentQuestionExtraction | None:
        """
        Return one extraction attempt by identifier.
        """

        self._validate_positive_integer(
            extraction_id,
            "extraction_id",
        )

        statement = select(
            AssessmentQuestionExtraction,
        ).where(
            AssessmentQuestionExtraction.id == extraction_id,
        )

        if include_relationships:
            statement = self._with_relationships(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalars().unique().one_or_none()

    async def get_by_id_and_assessment(
        self,
        *,
        extraction_id: int,
        assessment_id: int,
        include_relationships: bool = True,
    ) -> AssessmentQuestionExtraction | None:
        """
        Return an extraction only when it belongs to the supplied assessment.
        """

        self._validate_positive_integer(
            extraction_id,
            "extraction_id",
        )
        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        statement = select(
            AssessmentQuestionExtraction,
        ).where(
            AssessmentQuestionExtraction.id == extraction_id,
            AssessmentQuestionExtraction.assessment_id == assessment_id,
        )

        if include_relationships:
            statement = self._with_relationships(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalars().unique().one_or_none()

    async def get_by_document_and_version(
        self,
        *,
        assessment_document_id: int,
        version: int,
        include_relationships: bool = True,
    ) -> AssessmentQuestionExtraction | None:
        """
        Return one extraction attempt for a document/version pair.
        """

        self._validate_positive_integer(
            assessment_document_id,
            "assessment_document_id",
        )
        self._validate_positive_integer(
            version,
            "version",
        )

        statement = select(
            AssessmentQuestionExtraction,
        ).where(
            AssessmentQuestionExtraction.assessment_document_id
            == assessment_document_id,
            AssessmentQuestionExtraction.version == version,
        )

        if include_relationships:
            statement = self._with_relationships(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalars().unique().one_or_none()

    async def get_latest_for_document(
        self,
        *,
        assessment_document_id: int,
        include_relationships: bool = True,
    ) -> AssessmentQuestionExtraction | None:
        """
        Return the newest extraction attempt for a source document.
        """

        self._validate_positive_integer(
            assessment_document_id,
            "assessment_document_id",
        )

        statement = (
            select(
                AssessmentQuestionExtraction,
            )
            .where(
                AssessmentQuestionExtraction.assessment_document_id
                == assessment_document_id,
            )
            .order_by(
                AssessmentQuestionExtraction.version.desc(),
                AssessmentQuestionExtraction.id.desc(),
            )
            .limit(
                1,
            )
        )

        if include_relationships:
            statement = self._with_relationships(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalars().unique().first()

    async def list_for_document(
        self,
        *,
        assessment_document_id: int,
        include_relationships: bool = True,
    ) -> list[AssessmentQuestionExtraction]:
        """
        Return all extraction attempts for one source document.

        Newest attempts are returned first.
        """

        self._validate_positive_integer(
            assessment_document_id,
            "assessment_document_id",
        )

        statement = (
            select(
                AssessmentQuestionExtraction,
            )
            .where(
                AssessmentQuestionExtraction.assessment_document_id
                == assessment_document_id,
            )
            .order_by(
                AssessmentQuestionExtraction.version.desc(),
                AssessmentQuestionExtraction.id.desc(),
            )
        )

        if include_relationships:
            statement = self._with_relationships(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().unique().all(),
        )

    async def list_for_assessment(
        self,
        *,
        assessment_id: int,
        status: AssessmentQuestionExtractionStatus | str | None = None,
        include_relationships: bool = True,
    ) -> list[AssessmentQuestionExtraction]:
        """
        Return extraction attempts belonging to an assessment.

        Results are ordered newest first. An optional status filter may be
        supplied.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        statement = select(
            AssessmentQuestionExtraction,
        ).where(
            AssessmentQuestionExtraction.assessment_id == assessment_id,
        )

        if status is not None:
            statement = statement.where(
                AssessmentQuestionExtraction.status
                == self._normalise_status(
                    status,
                ),
            )

        statement = statement.order_by(
            AssessmentQuestionExtraction.created_at.desc(),
            AssessmentQuestionExtraction.id.desc(),
        )

        if include_relationships:
            statement = self._with_relationships(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return list(
            result.scalars().unique().all(),
        )

    async def get_next_version(
        self,
        *,
        assessment_document_id: int,
    ) -> int:
        """
        Return the next extraction version for a source document.

        The database unique constraint on
        ``(assessment_document_id, version)`` remains the final protection
        against concurrent attempts selecting the same next version.
        """

        self._validate_positive_integer(
            assessment_document_id,
            "assessment_document_id",
        )

        statement = select(
            func.max(
                AssessmentQuestionExtraction.version,
            ),
        ).where(
            AssessmentQuestionExtraction.assessment_document_id
            == assessment_document_id,
        )

        result = await self.db.execute(
            statement,
        )

        latest_version = result.scalar_one_or_none()

        if latest_version is None:
            return 1

        return (
            int(
                latest_version,
            )
            + 1
        )

    async def create(
        self,
        extraction: AssessmentQuestionExtraction,
    ) -> AssessmentQuestionExtraction:
        """
        Add and flush a new extraction attempt.
        """

        self._validate_positive_integer(
            extraction.assessment_id,
            "assessment_id",
        )
        self._validate_positive_integer(
            extraction.assessment_document_id,
            "assessment_document_id",
        )
        self._validate_positive_integer(
            extraction.requested_by_id,
            "requested_by_id",
        )
        self._validate_positive_integer(
            extraction.version,
            "version",
        )

        if extraction.imported_by_id is not None:
            self._validate_positive_integer(
                extraction.imported_by_id,
                "imported_by_id",
            )

        extraction.status = self._normalise_status(
            extraction.status,
        )

        if not extraction.extractor_name.strip():
            raise ValueError(
                "extractor_name cannot be blank.",
            )

        if len(extraction.extractor_name) > 100:
            raise ValueError(
                "extractor_name cannot exceed 100 characters.",
            )

        if (
            extraction.extractor_version is not None
            and len(extraction.extractor_version) > 50
        ):
            raise ValueError(
                "extractor_version cannot exceed 50 characters.",
            )

        if not extraction.parser_version.strip():
            raise ValueError(
                "parser_version cannot be blank.",
            )

        if len(extraction.parser_version) > 50:
            raise ValueError(
                "parser_version cannot exceed 50 characters.",
            )

        self.db.add(
            extraction,
        )

        await self.db.flush()
        await self.db.refresh(
            extraction,
        )

        return extraction

    async def save(
        self,
        extraction: AssessmentQuestionExtraction,
    ) -> AssessmentQuestionExtraction:
        """
        Flush changes to an existing extraction attempt.
        """

        if extraction.id is None:
            raise ValueError(
                "Cannot save an extraction without an ID.",
            )

        self._validate_positive_integer(
            extraction.id,
            "extraction.id",
        )
        self._validate_positive_integer(
            extraction.assessment_id,
            "assessment_id",
        )
        self._validate_positive_integer(
            extraction.assessment_document_id,
            "assessment_document_id",
        )
        self._validate_positive_integer(
            extraction.requested_by_id,
            "requested_by_id",
        )
        self._validate_positive_integer(
            extraction.version,
            "version",
        )

        if extraction.imported_by_id is not None:
            self._validate_positive_integer(
                extraction.imported_by_id,
                "imported_by_id",
            )

        extraction.status = self._normalise_status(
            extraction.status,
        )

        self.db.add(
            extraction,
        )

        await self.db.flush()
        await self.db.refresh(
            extraction,
        )

        return extraction

    async def mark_previous_completed_as_superseded(
        self,
        *,
        assessment_document_id: int,
        except_extraction_id: int | None = None,
    ) -> int:
        """
        Mark older completed proposals for a document as superseded.

        Imported extraction history is deliberately left untouched.
        Failed and pending attempts are also preserved in their original
        states.
        """

        self._validate_positive_integer(
            assessment_document_id,
            "assessment_document_id",
        )

        statement = select(
            AssessmentQuestionExtraction,
        ).where(
            AssessmentQuestionExtraction.assessment_document_id
            == assessment_document_id,
            AssessmentQuestionExtraction.status
            == AssessmentQuestionExtractionStatus.COMPLETED.value,
        )

        if except_extraction_id is not None:
            self._validate_positive_integer(
                except_extraction_id,
                "except_extraction_id",
            )

            statement = statement.where(
                AssessmentQuestionExtraction.id != except_extraction_id,
            )

        result = await self.db.execute(
            statement,
        )

        extractions = list(
            result.scalars().all(),
        )

        for extraction in extractions:
            extraction.status = AssessmentQuestionExtractionStatus.SUPERSEDED.value

        if extractions:
            await self.db.flush()

        return len(
            extractions,
        )
