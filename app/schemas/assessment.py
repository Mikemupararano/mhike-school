from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.models.assessment import AssessmentStatus
from app.models.assessment_question import (
    AssessmentQuestionAssetType,
    AssessmentQuestionType,
)

# ----------------------------------------------------------------------
# Assessment section schemas
# ----------------------------------------------------------------------


class AssessmentSectionCreate(BaseModel):
    """
    Payload used to create a section within a draft assessment.
    """

    title: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    order: int = Field(
        default=1,
        gt=0,
    )

    is_optional: bool = False


class AssessmentSectionUpdate(BaseModel):
    """
    Payload used to edit a section within a draft assessment.

    Fields are optional because PATCH semantics are used.
    """

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    order: int | None = Field(
        default=None,
        gt=0,
    )

    is_optional: bool | None = None


class AssessmentSectionOut(BaseModel):
    """
    Lightweight assessment-section representation.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    assessment_id: int

    title: str
    description: str | None = None

    order: int
    is_optional: bool


# ----------------------------------------------------------------------
# Assessment question option schemas
# ----------------------------------------------------------------------


class AssessmentQuestionOptionCreate(BaseModel):
    """
    Structured answer choice supplied when creating/replacing question options.

    ``is_correct`` is authoring/marking metadata and must never be exposed
    through a learner-facing response schema.
    """

    text: str = Field(
        min_length=1,
    )

    order: int = Field(
        default=1,
        gt=0,
    )

    is_correct: bool = False

    feedback: str | None = None


class AssessmentQuestionOptionUpdate(BaseModel):
    """
    PATCH-style update payload for one structured answer option.
    """

    text: str | None = Field(
        default=None,
        min_length=1,
    )

    order: int | None = Field(
        default=None,
        gt=0,
    )

    is_correct: bool | None = None

    feedback: str | None = None


class AssessmentQuestionOptionOut(BaseModel):
    """
    Teacher/admin representation of one structured answer option.

    This schema contains ``is_correct`` and therefore must not be reused by
    candidate endpoints.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    question_id: int

    text: str
    order: int
    is_correct: bool
    feedback: str | None = None


class AssessmentQuestionCandidateOptionOut(BaseModel):
    """
    Learner-safe representation of one structured answer option.

    Correctness and option feedback are intentionally absent.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    text: str
    order: int


# ----------------------------------------------------------------------
# Assessment question asset schemas
# ----------------------------------------------------------------------


class AssessmentQuestionAssetCreate(BaseModel):
    """
    Candidate-visible visual/resource attached to a canonical question.

    The binary file itself is stored outside the database; ``storage_path``
    records the server-side object/file reference.

    Source metadata preserves where an extracted visual came from in the
    uploaded question paper.
    """

    asset_type: AssessmentQuestionAssetType = AssessmentQuestionAssetType.FIGURE

    storage_path: str = Field(
        min_length=1,
    )

    original_filename: str | None = Field(
        default=None,
        max_length=255,
    )

    mime_type: str = Field(
        min_length=1,
        max_length=255,
    )

    file_size_bytes: int | None = Field(
        default=None,
        ge=0,
    )

    alt_text: str | None = None
    caption: str | None = None

    order: int = Field(
        default=1,
        gt=0,
    )

    candidate_visible: bool = True

    source_document_id: int | None = Field(
        default=None,
        gt=0,
    )

    source_page_number: int | None = Field(
        default=None,
        gt=0,
    )

    source_bbox: dict[str, object] | None = None


class AssessmentQuestionAssetUpdate(BaseModel):
    """
    PATCH-style update payload for a question asset.
    """

    asset_type: AssessmentQuestionAssetType | None = None

    storage_path: str | None = Field(
        default=None,
        min_length=1,
    )

    original_filename: str | None = Field(
        default=None,
        max_length=255,
    )

    mime_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    file_size_bytes: int | None = Field(
        default=None,
        ge=0,
    )

    alt_text: str | None = None
    caption: str | None = None

    order: int | None = Field(
        default=None,
        gt=0,
    )

    candidate_visible: bool | None = None

    source_document_id: int | None = Field(
        default=None,
        gt=0,
    )

    source_page_number: int | None = Field(
        default=None,
        gt=0,
    )

    source_bbox: dict[str, object] | None = None


class AssessmentQuestionAssetOut(BaseModel):
    """
    Teacher/admin representation of an attached question visual/resource.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    question_id: int

    asset_type: AssessmentQuestionAssetType
    storage_path: str

    original_filename: str | None = None
    mime_type: str
    file_size_bytes: int | None = None

    alt_text: str | None = None
    caption: str | None = None

    order: int
    candidate_visible: bool

    source_document_id: int | None = None
    source_page_number: int | None = None
    source_bbox: dict[str, object] | None = None


class AssessmentQuestionCandidateAssetOut(BaseModel):
    """
    Learner-safe metadata for a question visual/resource.

    ``storage_path`` and extraction provenance are intentionally omitted.
    Candidate APIs should supply an authorised delivery URL separately rather
    than exposing server-side storage locations.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    asset_type: AssessmentQuestionAssetType

    alt_text: str | None = None
    caption: str | None = None

    order: int


# ----------------------------------------------------------------------
# Assessment question interaction configuration schemas
# ----------------------------------------------------------------------


class AssessmentInteractionToolType(StrEnum):
    """
    Generic learner tool types supported by visual-response questions.

    Subject-specific palettes should compose these primitives rather than create
    new database columns or frontend-only question types.
    """

    SYMBOL = "symbol"
    PLOT_POINT = "plot_point"
    LINE = "line"
    CURVE = "curve"
    TEXT_LABEL = "text_label"
    AXIS_LABEL = "axis_label"
    ARROW = "arrow"
    LEADER_LINE = "leader_line"
    SHADE_REGION = "shade_region"
    FREE_DRAW = "free_draw"
    EQUATION_EDITOR = "equation_editor"
    EQUATION_MANIPULATION = "equation_manipulation"


class AssessmentInteractionToolConfig(BaseModel):
    """
    One tool made available to the learner for a visual-response question.

    ``tool_id`` is a stable machine identifier. ``label`` is learner-facing
    display text. ``symbol`` is required only for symbol tools and may contain
    Unicode such as ×, •, ○, +, − or other subject-specific notation.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    tool_id: str = Field(
        min_length=1,
        max_length=100,
    )

    tool_type: AssessmentInteractionToolType

    label: str = Field(
        min_length=1,
        max_length=255,
    )

    symbol: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    subject: str | None = Field(
        default=None,
        max_length=100,
    )

    @model_validator(
        mode="after",
    )
    def validate_tool(
        self,
    ) -> "AssessmentInteractionToolConfig":
        if (
            self.tool_type == AssessmentInteractionToolType.SYMBOL
            and self.symbol is None
        ):
            raise ValueError(
                "A symbol interaction tool must define a symbol.",
            )

        if (
            self.tool_type != AssessmentInteractionToolType.SYMBOL
            and self.symbol is not None
        ):
            raise ValueError(
                "Only symbol interaction tools may define a symbol.",
            )

        return self


class AssessmentQuestionInteractionConfig(BaseModel):
    """
    Versioned configuration for learner interaction with a question visual.

    The first version intentionally supports a broad palette/tool model. The
    same schema can represent atomic-structure symbols, magnetic-field markers,
    graph plotting, axis labels, leader lines, arrows, equation entry and
    step-by-step equation manipulation without hard-coding one subject into the
    pupil interface.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    version: Literal[1] = 1

    mode: Literal[
        "visual_annotation",
        "equation",
        "mixed",
    ] = "visual_annotation"

    palette_id: str | None = Field(
        default=None,
        max_length=100,
    )

    palette_label: str | None = Field(
        default=None,
        max_length=255,
    )

    coordinate_system: Literal["normalized", "graph"] = "normalized"

    snap_to_grid: bool = False

    tools: list[AssessmentInteractionToolConfig] = Field(
        default_factory=list,
        max_length=100,
    )

    max_annotations: int | None = Field(
        default=None,
        ge=1,
        le=500,
    )

    equation_format: Literal["latex"] = "latex"

    allow_equation_rearrangement: bool = False
    allow_equation_substitution: bool = False
    allow_equation_simplification: bool = False
    allow_equation_steps: bool = False

    allow_undo: bool = True
    allow_clear: bool = True

    @model_validator(
        mode="after",
    )
    def validate_config(
        self,
    ) -> "AssessmentQuestionInteractionConfig":
        tool_ids = [
            tool.tool_id
            for tool in self.tools
        ]

        if len(tool_ids) != len(set(tool_ids)):
            raise ValueError(
                "Interaction tool ids must be unique within one question.",
            )

        equation_tool_types = {
            AssessmentInteractionToolType.EQUATION_EDITOR,
            AssessmentInteractionToolType.EQUATION_MANIPULATION,
        }

        has_equation_tool = any(
            tool.tool_type in equation_tool_types
            for tool in self.tools
        )

        if (
            self.mode in {"equation", "mixed"}
            and not has_equation_tool
        ):
            raise ValueError(
                "Equation and mixed interaction modes must include an "
                "equation editor or equation manipulation tool.",
            )

        if (
            self.mode == "visual_annotation"
            and has_equation_tool
        ):
            raise ValueError(
                "Equation tools require equation or mixed interaction mode.",
            )

        if (
            self.allow_equation_rearrangement
            or self.allow_equation_substitution
            or self.allow_equation_simplification
            or self.allow_equation_steps
        ) and not has_equation_tool:
            raise ValueError(
                "Equation manipulation options require an equation tool.",
            )

        return self


# ----------------------------------------------------------------------
# Assessment question schemas
# ----------------------------------------------------------------------


def _validate_option_orders(
    options: list[AssessmentQuestionOptionCreate],
) -> None:
    """
    Ensure option order values are unique inside one question payload.
    """

    orders = [option.order for option in options]

    if len(orders) != len(set(orders)):
        raise ValueError(
            "Question option order values must be unique.",
        )


def _validate_asset_orders(
    assets: list[AssessmentQuestionAssetCreate],
) -> None:
    """
    Ensure asset order values are unique inside one question payload.
    """

    orders = [asset.order for asset in assets]

    if len(orders) != len(set(orders)):
        raise ValueError(
            "Question asset order values must be unique.",
        )


class AssessmentQuestionCreate(BaseModel):
    """
    Payload used to create a question within a draft assessment.

    Questions may optionally belong to a section and/or another question.

    Multiple-choice questions use structured ``options`` rather than embedding
    answer choices inside ``prompt``.

    Visuals required to answer a question are attached through ``assets`` so
    the same canonical diagram/graph/figure can be shown to the candidate and
    later to the marker.
    """

    section_id: int | None = Field(
        default=None,
        gt=0,
    )

    parent_question_id: int | None = Field(
        default=None,
        gt=0,
    )

    question_number: str = Field(
        min_length=1,
        max_length=50,
    )

    title: str | None = Field(
        default=None,
        max_length=255,
    )

    prompt: str | None = None

    question_type: AssessmentQuestionType = AssessmentQuestionType.WRITTEN

    interaction_config: AssessmentQuestionInteractionConfig | None = None

    maximum_mark: Decimal = Field(
        ge=Decimal("0"),
        max_digits=8,
        decimal_places=2,
    )

    order: int = Field(
        default=1,
        gt=0,
    )

    is_markable: bool = True

    options: list[AssessmentQuestionOptionCreate] = Field(
        default_factory=list,
    )

    assets: list[AssessmentQuestionAssetCreate] = Field(
        default_factory=list,
    )

    @model_validator(
        mode="after",
    )
    def validate_question_structure(
        self,
    ) -> "AssessmentQuestionCreate":
        """
        Validate interaction-specific authoring rules.

        Written/numeric questions do not use structured options.
        Single-choice/true-false questions require exactly one correct answer.
        Multiple-answer MCQs require one or more correct answers.
        Structural hierarchy nodes are non-markable and carry zero marks.
        """

        _validate_option_orders(
            self.options,
        )

        _validate_asset_orders(
            self.assets,
        )

        option_count = len(
            self.options,
        )

        correct_count = sum(1 for option in self.options if option.is_correct)

        if (
            self.question_type
            in {
                AssessmentQuestionType.WRITTEN,
                AssessmentQuestionType.NUMERIC,
                AssessmentQuestionType.STRUCTURAL,
            }
            and option_count > 0
        ):
            raise ValueError(
                "Written, numeric and structural questions cannot have "
                "multiple-choice options.",
            )

        if self.question_type == AssessmentQuestionType.MULTIPLE_CHOICE_SINGLE:
            if option_count < 2:
                raise ValueError(
                    "A single-answer multiple-choice question must have "
                    "at least two options.",
                )

            if correct_count != 1:
                raise ValueError(
                    "A single-answer multiple-choice question must have "
                    "exactly one correct option.",
                )

        if self.question_type == AssessmentQuestionType.MULTIPLE_CHOICE_MULTIPLE:
            if option_count < 2:
                raise ValueError(
                    "A multiple-answer multiple-choice question must have "
                    "at least two options.",
                )

            if correct_count < 1:
                raise ValueError(
                    "A multiple-answer multiple-choice question must have "
                    "at least one correct option.",
                )

        if self.question_type == AssessmentQuestionType.TRUE_FALSE:
            if option_count != 2:
                raise ValueError(
                    "A true/false question must have exactly two options.",
                )

            if correct_count != 1:
                raise ValueError(
                    "A true/false question must have exactly one correct " "option.",
                )

        if self.question_type == AssessmentQuestionType.DIAGRAM_ANNOTATION:
            if not self.assets:
                raise ValueError(
                    "A diagram-annotation question must include at least one asset.",
                )

            if self.interaction_config is None:
                raise ValueError(
                    "A diagram-annotation question must define interaction_config.",
                )

            if not self.interaction_config.tools:
                raise ValueError(
                    "A diagram-annotation interaction_config must define at least one tool.",
                )

            if self.interaction_config.mode not in {
                "visual_annotation",
                "mixed",
            }:
                raise ValueError(
                    "A diagram-annotation question must use visual_annotation "
                    "or mixed interaction mode.",
                )

        elif (
            self.interaction_config is not None
            and self.question_type
            not in {
                AssessmentQuestionType.WRITTEN,
                AssessmentQuestionType.NUMERIC,
            }
        ):
            raise ValueError(
                "interaction_config is currently supported for written, numeric "
                "and diagram-annotation questions.",
            )

        if (
            self.interaction_config is not None
            and self.question_type
            in {
                AssessmentQuestionType.WRITTEN,
                AssessmentQuestionType.NUMERIC,
            }
            and self.interaction_config.mode == "visual_annotation"
        ):
            raise ValueError(
                "Written and numeric questions with interaction_config must use "
                "equation or mixed mode.",
            )

        if self.question_type == AssessmentQuestionType.STRUCTURAL:
            if self.is_markable:
                raise ValueError(
                    "A structural question cannot be markable.",
                )

            if self.maximum_mark != Decimal("0"):
                raise ValueError(
                    "A structural question must have a maximum mark of zero.",
                )

        return self


class AssessmentQuestionUpdate(BaseModel):
    """
    Payload used to edit a question within a draft assessment.

    Fields are optional because PATCH semantics are used.

    Nullable relationship fields deliberately support explicit None:

        {"section_id": null}

    removes the section assignment, while omitting ``section_id`` leaves
    the current assignment unchanged.

    The endpoint must therefore inspect ``model_fields_set`` rather than
    relying only on field values.

    ``options`` and ``assets``, when supplied, represent complete replacement
    collections for that question. ``interaction_config`` is also replaceable as
    one versioned object. Service logic must apply the merged question state
    atomically.

    Cross-field rules that depend on the question's existing persisted values
    are deliberately enforced in the service layer for PATCH requests because
    a partial payload cannot validate state that was not supplied.
    """

    section_id: int | None = Field(
        default=None,
        gt=0,
    )

    parent_question_id: int | None = Field(
        default=None,
        gt=0,
    )

    question_number: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    title: str | None = Field(
        default=None,
        max_length=255,
    )

    prompt: str | None = None

    question_type: AssessmentQuestionType | None = None

    interaction_config: AssessmentQuestionInteractionConfig | None = None

    maximum_mark: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        max_digits=8,
        decimal_places=2,
    )

    order: int | None = Field(
        default=None,
        gt=0,
    )

    is_markable: bool | None = None

    options: list[AssessmentQuestionOptionCreate] | None = None

    assets: list[AssessmentQuestionAssetCreate] | None = None

    @model_validator(
        mode="after",
    )
    def validate_supplied_collections(
        self,
    ) -> "AssessmentQuestionUpdate":
        """
        Validate collection-local constraints that are safe under PATCH.

        Full interaction-type validation is deferred to the service after the
        payload has been merged with persisted question state.
        """

        if self.options is not None:
            _validate_option_orders(
                self.options,
            )

        if self.assets is not None:
            _validate_asset_orders(
                self.assets,
            )

        return self


class AssessmentQuestionOut(BaseModel):
    """
    Teacher/admin assessment-question representation.

    This output includes option correctness and server-side asset provenance,
    so candidate-facing endpoints must use dedicated learner-safe schemas.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    assessment_id: int

    section_id: int | None = None
    parent_question_id: int | None = None

    question_number: str

    title: str | None = None
    prompt: str | None = None

    question_type: AssessmentQuestionType

    interaction_config: AssessmentQuestionInteractionConfig | None = None

    maximum_mark: Decimal

    order: int
    is_markable: bool

    options: list[AssessmentQuestionOptionOut] = Field(
        default_factory=list,
    )

    assets: list[AssessmentQuestionAssetOut] = Field(
        default_factory=list,
    )


class AssessmentQuestionCandidateOut(BaseModel):
    """
    Learner-safe canonical question representation.

    Correct answers, mark-scheme information, server storage paths and source
    extraction metadata are intentionally excluded.

    Candidate APIs may attach an authorised asset URL when they serialize
    ``assets`` for delivery.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    assessment_id: int

    section_id: int | None = None
    parent_question_id: int | None = None

    question_number: str

    title: str | None = None
    prompt: str | None = None

    question_type: AssessmentQuestionType

    interaction_config: AssessmentQuestionInteractionConfig | None = None

    maximum_mark: Decimal

    order: int
    is_markable: bool

    options: list[AssessmentQuestionCandidateOptionOut] = Field(
        default_factory=list,
    )

    assets: list[AssessmentQuestionCandidateAssetOut] = Field(
        default_factory=list,
    )


# ----------------------------------------------------------------------
# Assessment definition schemas
# ----------------------------------------------------------------------


class AssessmentCreate(BaseModel):
    """
    Payload used to create a new draft assessment.
    """

    course_id: int = Field(
        gt=0,
    )

    title: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    assessment_type: str | None = Field(
        default=None,
        max_length=100,
    )

    academic_year: str | None = Field(
        default=None,
        max_length=50,
    )

    term: str | None = Field(
        default=None,
        max_length=100,
    )

    anonymous_marking: bool = False

    scheduled_at: datetime | None = None
    closes_at: datetime | None = None

    @model_validator(
        mode="after",
    )
    def validate_date_window(
        self,
    ) -> "AssessmentCreate":
        """
        Ensure the closing time follows the scheduled time.
        """

        if (
            self.scheduled_at is not None
            and self.closes_at is not None
            and self.closes_at <= self.scheduled_at
        ):
            raise ValueError(
                "Assessment closing time must be later than its scheduled time.",
            )

        return self


class AssessmentUpdate(BaseModel):
    """
    Payload used to edit an existing draft assessment.

    Fields are optional because PATCH semantics are used.
    """

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    assessment_type: str | None = Field(
        default=None,
        max_length=100,
    )

    academic_year: str | None = Field(
        default=None,
        max_length=50,
    )

    term: str | None = Field(
        default=None,
        max_length=100,
    )

    anonymous_marking: bool | None = None

    scheduled_at: datetime | None = None
    closes_at: datetime | None = None


class AssessmentStatusUpdate(BaseModel):
    """
    Payload for an explicit assessment lifecycle transition.
    """

    status: AssessmentStatus


class AssessmentOut(BaseModel):
    """
    Full teacher/admin assessment response model.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    school_id: int
    course_id: int
    created_by_id: int

    title: str
    description: str | None = None

    assessment_type: str | None = None
    academic_year: str | None = None
    term: str | None = None

    status: AssessmentStatus
    anonymous_marking: bool

    scheduled_at: datetime | None = None
    closes_at: datetime | None = None

    created_at: datetime
    updated_at: datetime

    sections: list[AssessmentSectionOut] = Field(
        default_factory=list,
    )

    questions: list[AssessmentQuestionOut] = Field(
        default_factory=list,
    )
