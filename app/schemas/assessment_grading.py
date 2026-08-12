from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.models.assessment_grading import AssessmentGradingBasis

# ---------------------------------------------------------------------------
# Grade boundary schemas
# ---------------------------------------------------------------------------


class AssessmentGradeBoundaryBase(BaseModel):
    """
    Shared grade-boundary fields.

    ``minimum_value`` is inclusive.

    Examples:

        Percentage grading:
            Grade 9 >= 80
            Grade 8 >= 70

        Raw-mark grading:
            A* >= 72
            A  >= 64
    """

    grade_label: str = Field(
        min_length=1,
        max_length=50,
    )

    minimum_value: Decimal = Field(
        ge=0,
    )

    order: int = Field(
        ge=1,
    )

    description: str | None = None

    grade_points: Decimal | None = Field(
        default=None,
        ge=0,
    )

    is_pass: bool | None = None

    @field_validator(
        "grade_label",
    )
    @classmethod
    def validate_grade_label(
        cls,
        value: str,
    ) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError(
                "grade_label cannot be blank.",
            )

        return cleaned

    @field_validator(
        "description",
    )
    @classmethod
    def clean_description(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()

        return cleaned or None


class AssessmentGradeBoundaryCreate(
    AssessmentGradeBoundaryBase,
):
    """
    Payload for creating one assessment grade boundary.
    """

    pass


class AssessmentGradeBoundaryUpdate(BaseModel):
    """
    Partial payload for updating one grade boundary.
    """

    grade_label: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    minimum_value: Decimal | None = Field(
        default=None,
        ge=0,
    )

    order: int | None = Field(
        default=None,
        ge=1,
    )

    description: str | None = None

    grade_points: Decimal | None = Field(
        default=None,
        ge=0,
    )

    is_pass: bool | None = None

    @field_validator(
        "grade_label",
    )
    @classmethod
    def validate_grade_label(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()

        if not cleaned:
            raise ValueError(
                "grade_label cannot be blank.",
            )

        return cleaned

    @field_validator(
        "description",
    )
    @classmethod
    def clean_description(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()

        return cleaned or None


class AssessmentGradeBoundaryOut(BaseModel):
    """
    Public representation of one grade boundary.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    grading_scheme_id: int

    grade_label: str
    minimum_value: Decimal
    order: int

    description: str | None = None

    grade_points: Decimal | None = None
    is_pass: bool | None = None

    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Grading scheme schemas
# ---------------------------------------------------------------------------


class AssessmentGradingSchemeBase(BaseModel):
    """
    Shared grading-scheme fields.
    """

    name: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    basis: AssessmentGradingBasis = AssessmentGradingBasis.PERCENTAGE

    is_active: bool = True

    @field_validator(
        "name",
    )
    @classmethod
    def validate_name(
        cls,
        value: str,
    ) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError(
                "name cannot be blank.",
            )

        return cleaned

    @field_validator(
        "description",
    )
    @classmethod
    def clean_description(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()

        return cleaned or None


class AssessmentGradingSchemeCreate(
    AssessmentGradingSchemeBase,
):
    """
    Payload for creating an assessment grading scheme.
    """

    pass


class AssessmentGradingSchemeUpdate(BaseModel):
    """
    Partial payload for updating an assessment grading scheme.
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    basis: AssessmentGradingBasis | None = None

    is_active: bool | None = None

    @field_validator(
        "name",
    )
    @classmethod
    def validate_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()

        if not cleaned:
            raise ValueError(
                "name cannot be blank.",
            )

        return cleaned

    @field_validator(
        "description",
    )
    @classmethod
    def clean_description(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()

        return cleaned or None


class AssessmentGradingSchemeOut(BaseModel):
    """
    Public representation of one grading scheme and its boundaries.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    assessment_id: int

    name: str
    description: str | None = None

    basis: AssessmentGradingBasis
    is_active: bool

    created_by_id: int

    created_at: datetime
    updated_at: datetime

    boundaries: list[AssessmentGradeBoundaryOut] = Field(
        default_factory=list,
    )


# ---------------------------------------------------------------------------
# Explicit grade-resolution schemas
# ---------------------------------------------------------------------------


class AssessmentGradeResolveRequest(BaseModel):
    """
    Resolve an explicit grading value against the active grading scheme.

    The value must be expressed in the grading scheme's configured basis:

        percentage
            0 to 100

        raw_mark
            0 to assessment maximum mark
    """

    value: Decimal = Field(
        ge=0,
    )


class AssessmentGradeResolutionOut(BaseModel):
    """
    Result of resolving one value against an active grading scheme.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    assessment_id: int

    grading_scheme_id: int
    grading_scheme_name: str

    basis: AssessmentGradingBasis

    value: Decimal

    grade: str | None = None
    boundary_id: int | None = None
    minimum_value: Decimal | None = None

    grade_points: Decimal | None = None
    is_pass: bool | None = None


# ---------------------------------------------------------------------------
# Script grading schemas
# ---------------------------------------------------------------------------


class AssessmentScriptGradeOut(BaseModel):
    """
    Derived grade for one assessment script version.

    ``result_stage`` identifies which assessment-result stage was used:

        current
            Includes provisional marks.

        completed
            Includes MARKED, REVIEWED and FINALISED marks.

        finalised
            Includes FINALISED marks only.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    assessment_id: int
    candidate_id: int
    student_id: int

    script_id: int
    script_version: int

    result_stage: str

    grading_scheme_id: int
    grading_scheme_name: str

    basis: AssessmentGradingBasis

    value: Decimal | None = None

    grade: str | None = None
    boundary_id: int | None = None
    minimum_value: Decimal | None = None

    grade_points: Decimal | None = None
    is_pass: bool | None = None

    @field_validator(
        "result_stage",
    )
    @classmethod
    def validate_result_stage(
        cls,
        value: str,
    ) -> str:
        cleaned = value.strip().lower()

        allowed = {
            "current",
            "completed",
            "finalised",
        }

        if cleaned not in allowed:
            raise ValueError(
                "result_stage must be one of: " "current, completed, finalised.",
            )

        return cleaned


# ---------------------------------------------------------------------------
# Candidate grading schemas
# ---------------------------------------------------------------------------


class AssessmentCandidateGradeOut(
    AssessmentScriptGradeOut,
):
    """
    Derived grade for the candidate's latest assessment script.

    The current service resolves the candidate's highest script version and
    returns the same grading representation used for script grading.
    """

    pass


# ---------------------------------------------------------------------------
# Boundary list container
# ---------------------------------------------------------------------------


class AssessmentGradeBoundaryListOut(BaseModel):
    """
    Container for boundaries belonging to one grading scheme.
    """

    grading_scheme_id: int

    boundaries: list[AssessmentGradeBoundaryOut] = Field(
        default_factory=list,
    )
