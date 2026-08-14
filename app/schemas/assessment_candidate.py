from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.assessment_candidate import (
    AssessmentCandidateStatus,
    AssessmentScriptStatus,
)


class AssessmentCandidateAllocate(BaseModel):
    """
    Payload for allocating a student to an assessment.
    """

    student_id: int = Field(
        gt=0,
    )

    candidate_number: str | None = Field(
        default=None,
        max_length=100,
    )

    access_arrangements: str | None = None


class AssessmentCandidateBulkAllocate(BaseModel):
    """
    Payload for allocating multiple students to an assessment.
    """

    student_ids: list[int] = Field(
        min_length=1,
    )


class AssessmentCandidateBulkItemOut(BaseModel):
    """
    Result for one unique student in a bulk allocation.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    student_id: int
    outcome: str
    candidate_id: int | None = None
    detail: str | None = None


class AssessmentCandidateBulkOut(BaseModel):
    """
    Summary of one bulk candidate-allocation operation.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    assessment_id: int
    source: str
    class_id: int | None = None

    requested_count: int
    unique_requested_count: int

    created_count: int
    already_allocated_count: int
    ineligible_count: int

    items: list[AssessmentCandidateBulkItemOut] = Field(
        default_factory=list,
    )


class AssessmentCandidateClassPreviewOut(BaseModel):
    """
    Read-only preview of class-to-assessment allocation.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    assessment_id: int
    class_id: int
    class_name: str

    allocation_allowed: bool

    enrolled_count: int
    student_count: int

    eligible_count: int
    already_allocated_count: int
    ineligible_count: int

    eligible_student_ids: list[int] = Field(
        default_factory=list,
    )

    already_allocated_student_ids: list[int] = Field(
        default_factory=list,
    )

    ineligible_student_ids: list[int] = Field(
        default_factory=list,
    )


class AssessmentCandidateUpdate(BaseModel):
    """
    Payload for updating candidate metadata.
    """

    candidate_number: str | None = Field(
        default=None,
        max_length=100,
    )

    access_arrangements: str | None = None


class AssessmentCandidateStatusUpdate(BaseModel):
    """
    Payload for an explicit candidate lifecycle transition.
    """

    status: AssessmentCandidateStatus


class AssessmentScriptCreate(BaseModel):
    """
    Payload for creating the next script version for a candidate.
    """

    source_type: str | None = Field(
        default=None,
        max_length=100,
    )

    source_filename: str | None = Field(
        default=None,
        max_length=500,
    )

    storage_key: str | None = Field(
        default=None,
        max_length=1000,
    )

    mime_type: str | None = Field(
        default=None,
        max_length=255,
    )

    checksum: str | None = Field(
        default=None,
        max_length=255,
    )


class AssessmentScriptStatusUpdate(BaseModel):
    """
    Payload for an explicit script lifecycle transition.
    """

    status: AssessmentScriptStatus


class AssessmentScriptOut(BaseModel):
    """
    Assessment script response model.

    Responses and marking data are intentionally excluded from this standard
    representation because those belong to dedicated marking workflows.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    candidate_id: int
    version: int
    status: AssessmentScriptStatus

    source_type: str | None = None
    source_filename: str | None = None
    storage_key: str | None = None
    mime_type: str | None = None
    checksum: str | None = None

    created_at: datetime
    submitted_at: datetime | None = None
    marking_started_at: datetime | None = None
    marked_at: datetime | None = None
    finalised_at: datetime | None = None


class AssessmentCandidateOut(BaseModel):
    """
    Assessment candidate response model.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    assessment_id: int
    student_id: int
    status: AssessmentCandidateStatus

    candidate_number: str | None = None
    access_arrangements: str | None = None

    allocated_at: datetime
    started_at: datetime | None = None
    submitted_at: datetime | None = None

    scripts: list[AssessmentScriptOut] = Field(
        default_factory=list,
    )
