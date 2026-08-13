from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.models.assessment_feedback import AssessmentFeedbackStatus

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


AssessmentFeedbackStatusValue = Literal[
    "draft",
    "finalised",
    "archived",
]


# ---------------------------------------------------------------------------
# Overall feedback create
# ---------------------------------------------------------------------------


class AssessmentFeedbackCreate(BaseModel):
    """
    Payload used to create overall structured feedback for one script.
    """

    school_id: int | None = Field(
        default=None,
        ge=1,
    )

    script_id: int = Field(
        ge=1,
    )

    overall_comment: str | None = None

    strengths: str | None = None

    areas_for_improvement: str | None = None

    next_steps: str | None = None

    include_with_result: bool = True


# ---------------------------------------------------------------------------
# Overall feedback update
# ---------------------------------------------------------------------------


class AssessmentFeedbackUpdate(BaseModel):
    """
    PATCH-style overall feedback update.

    Omitted fields remain unchanged.

    Nullable text fields may explicitly be supplied as None to clear them.
    """

    overall_comment: str | None = None

    strengths: str | None = None

    areas_for_improvement: str | None = None

    next_steps: str | None = None

    include_with_result: bool | None = None


# ---------------------------------------------------------------------------
# Overall feedback output
# ---------------------------------------------------------------------------


class AssessmentFeedbackOut(BaseModel):
    """
    Fully resolved overall assessment feedback.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    school_id: int

    script_id: int

    overall_comment: str | None = None

    strengths: str | None = None

    areas_for_improvement: str | None = None

    next_steps: str | None = None

    status: AssessmentFeedbackStatusValue

    include_with_result: bool

    created_by_id: int

    created_by_name: str | None = None

    updated_by_id: int | None = None

    updated_by_name: str | None = None

    finalised_at: datetime | None = None

    finalised_by_id: int | None = None

    finalised_by_name: str | None = None

    created_at: datetime

    updated_at: datetime


# ---------------------------------------------------------------------------
# Question feedback create
# ---------------------------------------------------------------------------


class AssessmentQuestionFeedbackCreate(BaseModel):
    """
    Payload used to create feedback for one assessment response.
    """

    school_id: int | None = Field(
        default=None,
        ge=1,
    )

    response_id: int = Field(
        ge=1,
    )

    feedback_text: str | None = None

    strength: str | None = None

    improvement: str | None = None

    include_with_result: bool = True


# ---------------------------------------------------------------------------
# Question feedback update
# ---------------------------------------------------------------------------


class AssessmentQuestionFeedbackUpdate(BaseModel):
    """
    PATCH-style question feedback update.

    Omitted fields remain unchanged.

    Nullable text fields may explicitly be supplied as None to clear them.
    """

    feedback_text: str | None = None

    strength: str | None = None

    improvement: str | None = None

    include_with_result: bool | None = None


# ---------------------------------------------------------------------------
# Question feedback output
# ---------------------------------------------------------------------------


class AssessmentQuestionFeedbackOut(BaseModel):
    """
    Fully resolved question-specific assessment feedback.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    school_id: int

    response_id: int

    feedback_text: str | None = None

    strength: str | None = None

    improvement: str | None = None

    include_with_result: bool

    created_by_id: int

    created_by_name: str | None = None

    updated_by_id: int | None = None

    updated_by_name: str | None = None

    created_at: datetime

    updated_at: datetime


# ---------------------------------------------------------------------------
# Workflow action responses
# ---------------------------------------------------------------------------


class AssessmentFeedbackWorkflowOut(BaseModel):
    """
    Response returned after finalising or reopening overall feedback.
    """

    id: int

    status: AssessmentFeedbackStatusValue

    finalised_at: datetime | None = None

    finalised_by_id: int | None = None

    finalised_by_name: str | None = None


# ---------------------------------------------------------------------------
# Future student/parent visibility payloads
# ---------------------------------------------------------------------------


class PublishedAssessmentQuestionFeedbackOut(BaseModel):
    """
    Question-level feedback safe to expose with an authorised published result.
    """

    response_id: int

    feedback_text: str | None = None

    strength: str | None = None

    improvement: str | None = None


class PublishedAssessmentFeedbackOut(BaseModel):
    """
    Structured feedback safe to expose with an authorised published result.

    This schema does not itself grant visibility. Publication and audience
    checks remain the responsibility of the service layer.
    """

    script_id: int

    overall_comment: str | None = None

    strengths: str | None = None

    areas_for_improvement: str | None = None

    next_steps: str | None = None

    question_feedback: list[PublishedAssessmentQuestionFeedbackOut] = Field(
        default_factory=list,
    )
