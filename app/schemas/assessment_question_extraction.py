from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.models.assessment_question_extraction import (
    AssessmentQuestionExtractionStatus,
)


class AssessmentQuestionExtractionSource(BaseModel):
    """
    Source evidence identifying where a proposed question was detected.
    """

    model_config = ConfigDict(
        extra="allow",
    )

    page_number: int = Field(
        ge=1,
    )
    line_number: int | None = Field(
        default=None,
        ge=1,
    )
    source_line: str | None = None


class AssessmentQuestionExtractionCandidate(BaseModel):
    """
    One machine-detected question candidate awaiting teacher review.

    The candidate is deliberately separate from the canonical
    AssessmentQuestion model. Extraction alone never creates live questions.
    """

    model_config = ConfigDict(
        extra="allow",
    )

    question_number: str = Field(
        min_length=1,
    )
    text: str = ""
    marks: int | None = Field(
        default=None,
        ge=0,
    )
    depth: int = Field(
        default=0,
        ge=0,
    )
    source: AssessmentQuestionExtractionSource
    confidence: str = "candidate"
    requires_review: bool = True


class AssessmentQuestionExtractionWarning(BaseModel):
    """
    Warning generated while reading or interpreting the source PDF.
    """

    model_config = ConfigDict(
        extra="allow",
    )

    code: str = Field(
        min_length=1,
    )
    message: str = Field(
        min_length=1,
    )
    page_numbers: list[int] = Field(
        default_factory=list,
    )


class AssessmentQuestionExtractionProposalSummary(BaseModel):
    """
    Summary statistics generated from an extraction proposal.
    """

    model_config = ConfigDict(
        extra="allow",
    )

    detected_question_count: int = Field(
        default=0,
        ge=0,
    )
    questions_with_detected_marks: int = Field(
        default=0,
        ge=0,
    )
    detected_mark_sum: int = Field(
        default=0,
        ge=0,
    )


class AssessmentQuestionExtractionProposal(BaseModel):
    """
    Reviewable machine-generated interpretation of a question paper.

    ``auto_import_allowed`` remains false for the current parser architecture.
    A teacher must explicitly review and import the proposal before canonical
    assessment questions are created.
    """

    model_config = ConfigDict(
        extra="allow",
    )

    parser_version: str = Field(
        min_length=1,
    )
    review_required: bool = True
    auto_import_allowed: bool = False
    questions: list[AssessmentQuestionExtractionCandidate] = Field(
        default_factory=list,
    )
    summary: AssessmentQuestionExtractionProposalSummary
    warnings: list[AssessmentQuestionExtractionWarning] = Field(
        default_factory=list,
    )


class AssessmentQuestionExtractionPageCandidate(BaseModel):
    """
    Candidate question detected directly from one source page.
    """

    model_config = ConfigDict(
        extra="allow",
    )

    question_number: str = Field(
        min_length=1,
    )
    text: str = ""
    marks: int | None = Field(
        default=None,
        ge=0,
    )
    page_number: int = Field(
        ge=1,
    )
    line_number: int = Field(
        ge=1,
    )
    source_line: str


class AssessmentQuestionExtractionPage(BaseModel):
    """
    Extracted evidence retained for one PDF page.
    """

    model_config = ConfigDict(
        extra="allow",
    )

    page_number: int = Field(
        ge=1,
    )
    has_extractable_text: bool
    text_length: int = Field(
        ge=0,
    )
    text: str = ""
    question_candidates: list[AssessmentQuestionExtractionPageCandidate] = Field(
        default_factory=list,
    )
    extraction_error: str | None = None


class AssessmentQuestionExtractionBaseResponse(BaseModel):
    """
    Shared extraction metadata returned through the API.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    assessment_id: int
    assessment_document_id: int
    requested_by_id: int
    imported_by_id: int | None = None

    version: int = Field(
        ge=1,
    )

    status: AssessmentQuestionExtractionStatus

    extractor_name: str
    extractor_version: str | None = None
    parser_version: str

    page_count: int | None = Field(
        default=None,
        ge=0,
    )
    text_page_count: int | None = Field(
        default=None,
        ge=0,
    )

    detected_question_count: int | None = Field(
        default=None,
        ge=0,
    )
    detected_markable_question_count: int | None = Field(
        default=None,
        ge=0,
    )
    detected_total_marks: int | None = Field(
        default=None,
        ge=0,
    )

    error_message: str | None = None

    started_at: datetime | None = None
    completed_at: datetime | None = None
    imported_at: datetime | None = None

    created_at: datetime
    updated_at: datetime


class AssessmentQuestionExtractionSummaryResponse(
    AssessmentQuestionExtractionBaseResponse,
):
    """
    Lightweight extraction response for history/status listings.

    Large page text and proposal JSON are intentionally omitted.
    """

    pass


class AssessmentQuestionExtractionResponse(
    AssessmentQuestionExtractionBaseResponse,
):
    """
    Full extraction response used by the review workspace.
    """

    source_metadata: dict[str, Any] | None = None

    page_data: list[AssessmentQuestionExtractionPage] | None = None

    proposal_data: AssessmentQuestionExtractionProposal | None = None


class AssessmentQuestionExtractionCreatedResponse(
    AssessmentQuestionExtractionResponse,
):
    """
    Response returned when a new extraction attempt is created.
    """

    message: str = "Question-paper extraction completed."


class AssessmentQuestionExtractionHistoryResponse(BaseModel):
    """
    Extraction history for one source question-paper document.
    """

    assessment_id: int
    assessment_document_id: int

    extractions: list[AssessmentQuestionExtractionSummaryResponse] = Field(
        default_factory=list,
    )
