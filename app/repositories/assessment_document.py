from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment_document import AssessmentDocument


class AssessmentDocumentRepository:
    """
    Repository for assessment-document persistence and lookup.

    The repository deliberately does not commit or roll back transactions.
    Transaction ownership remains with the calling service or endpoint.

    Assessment documents are versioned rather than overwritten. Replacing a
    question paper therefore marks the previous document as non-current while
    preserving its database record and source-file metadata.
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
    def _normalise_document_type(
        document_type: str,
    ) -> str:
        """
        Return a validated document-type identifier.
        """

        normalised = document_type.strip().lower()

        if not normalised:
            raise ValueError(
                "document_type cannot be blank.",
            )

        if len(normalised) > 50:
            raise ValueError(
                "document_type cannot exceed 50 characters.",
            )

        return normalised

    @staticmethod
    def _with_relationships(
        statement,
    ):
        """
        Apply standard eager loading for assessment documents.
        """

        return statement.options(
            selectinload(
                AssessmentDocument.assessment,
            ),
            selectinload(
                AssessmentDocument.uploaded_by,
            ),
        )

    async def get_by_id(
        self,
        document_id: int,
        *,
        include_relationships: bool = True,
    ) -> AssessmentDocument | None:
        """
        Return one assessment document by global identifier.

        School-facing workflows should normally use
        ``get_by_id_and_assessment`` so the assessment boundary is enforced in
        the database query itself.
        """

        self._validate_positive_integer(
            document_id,
            "document_id",
        )

        statement = select(
            AssessmentDocument,
        ).where(
            AssessmentDocument.id == document_id,
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
        document_id: int,
        assessment_id: int,
        include_relationships: bool = True,
    ) -> AssessmentDocument | None:
        """
        Return one document only when it belongs to the supplied assessment.
        """

        self._validate_positive_integer(
            document_id,
            "document_id",
        )
        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        statement = select(
            AssessmentDocument,
        ).where(
            AssessmentDocument.id == document_id,
            AssessmentDocument.assessment_id == assessment_id,
        )

        if include_relationships:
            statement = self._with_relationships(
                statement,
            )

        result = await self.db.execute(
            statement,
        )

        return result.scalars().unique().one_or_none()

    async def get_current(
        self,
        *,
        assessment_id: int,
        document_type: str = "question_paper",
        include_relationships: bool = True,
    ) -> AssessmentDocument | None:
        """
        Return the current document of the requested type for an assessment.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        normalised_document_type = self._normalise_document_type(
            document_type,
        )

        statement = (
            select(
                AssessmentDocument,
            )
            .where(
                AssessmentDocument.assessment_id == assessment_id,
                AssessmentDocument.document_type == normalised_document_type,
                AssessmentDocument.is_current.is_(True),
            )
            .order_by(
                AssessmentDocument.created_at.desc(),
                AssessmentDocument.id.desc(),
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

    async def list_for_assessment(
        self,
        *,
        assessment_id: int,
        document_type: str | None = None,
        current_only: bool = False,
        include_relationships: bool = True,
    ) -> list[AssessmentDocument]:
        """
        Return documents attached to an assessment.

        By default this includes historical document versions so replaced
        source papers remain available for audit and future recovery.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        statement = select(
            AssessmentDocument,
        ).where(
            AssessmentDocument.assessment_id == assessment_id,
        )

        if document_type is not None:
            normalised_document_type = self._normalise_document_type(
                document_type,
            )

            statement = statement.where(
                AssessmentDocument.document_type == normalised_document_type,
            )

        if current_only:
            statement = statement.where(
                AssessmentDocument.is_current.is_(True),
            )

        statement = statement.order_by(
            AssessmentDocument.created_at.desc(),
            AssessmentDocument.id.desc(),
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

    async def mark_current_as_replaced(
        self,
        *,
        assessment_id: int,
        document_type: str = "question_paper",
    ) -> int:
        """
        Mark every current document of the supplied type as non-current.

        Normally there should be at most one current document. Updating all
        matching rows makes replacement resilient if historical data ever
        contains more than one current record.

        Returns the number of rows affected where supported by the database
        driver.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        normalised_document_type = self._normalise_document_type(
            document_type,
        )

        result = await self.db.execute(
            update(
                AssessmentDocument,
            )
            .where(
                AssessmentDocument.assessment_id == assessment_id,
                AssessmentDocument.document_type == normalised_document_type,
                AssessmentDocument.is_current.is_(True),
            )
            .values(
                is_current=False,
            )
        )

        await self.db.flush()

        rowcount = getattr(
            result,
            "rowcount",
            0,
        )

        return int(
            rowcount or 0,
        )

    async def create(
        self,
        document: AssessmentDocument,
    ) -> AssessmentDocument:
        """
        Add and flush a new assessment document.
        """

        self._validate_positive_integer(
            document.assessment_id,
            "assessment_id",
        )
        self._validate_positive_integer(
            document.uploaded_by_id,
            "uploaded_by_id",
        )

        document.document_type = self._normalise_document_type(
            document.document_type,
        )

        if not document.original_filename.strip():
            raise ValueError(
                "original_filename cannot be blank.",
            )

        if len(document.original_filename) > 500:
            raise ValueError(
                "original_filename cannot exceed 500 characters.",
            )

        if not document.stored_filename.strip():
            raise ValueError(
                "stored_filename cannot be blank.",
            )

        if len(document.stored_filename) > 500:
            raise ValueError(
                "stored_filename cannot exceed 500 characters.",
            )

        if not document.storage_path.strip():
            raise ValueError(
                "storage_path cannot be blank.",
            )

        if len(document.storage_path) > 2000:
            raise ValueError(
                "storage_path cannot exceed 2000 characters.",
            )

        if not document.mime_type.strip():
            raise ValueError(
                "mime_type cannot be blank.",
            )

        if len(document.mime_type) > 255:
            raise ValueError(
                "mime_type cannot exceed 255 characters.",
            )

        if (
            not isinstance(document.file_size_bytes, int)
            or isinstance(document.file_size_bytes, bool)
            or document.file_size_bytes < 1
        ):
            raise ValueError(
                "file_size_bytes must be a positive integer.",
            )

        self.db.add(
            document,
        )

        await self.db.flush()
        await self.db.refresh(
            document,
        )

        return document

    async def save(
        self,
        document: AssessmentDocument,
    ) -> AssessmentDocument:
        """
        Flush changes to an existing assessment document.
        """

        if document.id is None:
            raise ValueError(
                "Cannot save an assessment document without an ID.",
            )

        self._validate_positive_integer(
            document.id,
            "document.id",
        )
        self._validate_positive_integer(
            document.assessment_id,
            "assessment_id",
        )
        self._validate_positive_integer(
            document.uploaded_by_id,
            "uploaded_by_id",
        )

        document.document_type = self._normalise_document_type(
            document.document_type,
        )

        self.db.add(
            document,
        )

        await self.db.flush()
        await self.db.refresh(
            document,
        )

        return document

    async def delete(
        self,
        document: AssessmentDocument,
    ) -> None:
        """
        Delete a document database record and flush the change.

        Ordinary question-paper replacement should not call this method.
        Historical source documents are preserved by setting ``is_current``
        to False instead.
        """

        if document.id is None:
            raise ValueError(
                "Cannot delete an assessment document without an ID.",
            )

        self._validate_positive_integer(
            document.id,
            "document.id",
        )

        await self.db.delete(
            document,
        )
        await self.db.flush()
