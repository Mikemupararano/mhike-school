from __future__ import annotations

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class AssessmentDocumentBase(BaseModel):
    """
    Shared assessment-document metadata.

    The first supported document type is a question paper. The schema is
    deliberately generic enough to support mark schemes and other assessment
    documents later without changing the storage model.
    """

    document_type: str = Field(
        default="question_paper",
        min_length=1,
        max_length=50,
    )

    original_filename: str = Field(
        min_length=1,
        max_length=500,
    )

    mime_type: str = Field(
        min_length=1,
        max_length=255,
    )

    file_size_bytes: int = Field(
        gt=0,
    )


class AssessmentDocumentRead(AssessmentDocumentBase):
    """
    Public metadata returned for one stored assessment document.

    Internal storage paths and generated storage filenames are deliberately
    excluded from the ordinary API response.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    assessment_id: int
    uploaded_by_id: int

    is_current: bool

    extraction_requested: bool
    extraction_completed: bool
    extraction_error: str | None = None

    created_at: datetime
    updated_at: datetime


class AssessmentDocumentUploadResponse(AssessmentDocumentRead):
    """
    Response returned after a successful question-paper upload.
    """

    message: str = "Question paper uploaded successfully."


class AssessmentDocumentListResponse(BaseModel):
    """
    Collection response for assessment documents.

    Keeping this as an explicit response object allows us to add pagination or
    document-type grouping later without breaking clients.
    """

    assessment_id: int
    documents: list[AssessmentDocumentRead]


class AssessmentDocumentDownloadInfo(BaseModel):
    """
    Safe metadata returned when resolving a downloadable assessment document.

    The actual file download endpoint will return the file response itself.
    This schema remains useful for frontend metadata and future signed-URL
    storage.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    assessment_id: int
    original_filename: str
    mime_type: str
    file_size_bytes: int
    is_current: bool
