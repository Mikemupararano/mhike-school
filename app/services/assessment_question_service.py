from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus
from app.models.assessment_question import (
    AssessmentQuestion,
    AssessmentQuestionAsset,
    AssessmentQuestionAssetType,
    AssessmentQuestionOption,
    AssessmentQuestionType,
    AssessmentSection,
)
from app.models.user import User
from app.repositories.assessment import AssessmentRepository
from app.repositories.assessment_question import AssessmentQuestionRepository
from app.schemas.assessment import (
    AssessmentQuestionAssetCreate,
    AssessmentQuestionOptionCreate,
)
from app.services.assessment_service import (
    _ensure_assessment_management_access,
)

# ----------------------------------------------------------------------
# Assessment access helpers
# ----------------------------------------------------------------------


async def _get_manageable_draft_assessment(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    *,
    include_relationships: bool = False,
) -> Assessment:
    """
    Return an assessment that the current user may structurally edit.

    Assessment sections and questions form part of the assessment definition,
    so they may be changed only while the assessment remains in DRAFT state.
    """

    assessment = await AssessmentRepository(
        db,
    ).get_by_id(
        assessment_id,
        include_relationships=include_relationships,
    )

    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )

    await _ensure_assessment_management_access(
        db,
        current_user,
        assessment,
    )

    if assessment.status != AssessmentStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Assessment sections and questions can only be changed "
                "while the assessment is in draft"
            ),
        )

    return assessment


async def _reload_assessment(
    db: AsyncSession,
    assessment_id: int,
) -> Assessment:
    """
    Reload an assessment with its standard relationships populated.

    AssessmentRepository uses populate_existing=True for relationship loading,
    so this refreshes in-session section/question collections after mutations.
    """

    assessment = await AssessmentRepository(
        db,
    ).get_by_id(
        assessment_id,
        include_relationships=True,
    )

    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )

    return assessment


# ----------------------------------------------------------------------
# Section helpers
# ----------------------------------------------------------------------


async def _get_section_or_404(
    db: AsyncSession,
    *,
    assessment_id: int,
    section_id: int,
) -> AssessmentSection:
    """
    Return a section belonging to the supplied assessment.
    """

    section = await AssessmentQuestionRepository(
        db,
    ).get_section_by_id_and_assessment(
        section_id=section_id,
        assessment_id=assessment_id,
        include_relationships=True,
    )

    if section is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment section not found",
        )

    return section


async def _ensure_section_order_available(
    repository: AssessmentQuestionRepository,
    *,
    assessment_id: int,
    order: int,
    exclude_section_id: int | None = None,
) -> None:
    """
    Ensure a section order is not already occupied.
    """

    if await repository.section_order_exists(
        assessment_id=assessment_id,
        order=order,
        exclude_section_id=exclude_section_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(f"Assessment section order {order} " "is already in use"),
        )


# ----------------------------------------------------------------------
# Question helpers
# ----------------------------------------------------------------------


async def _get_question_or_404(
    db: AsyncSession,
    *,
    assessment_id: int,
    question_id: int,
) -> AssessmentQuestion:
    """
    Return a question belonging to the supplied assessment.
    """

    question = await AssessmentQuestionRepository(
        db,
    ).get_question_by_id_and_assessment(
        question_id=question_id,
        assessment_id=assessment_id,
        include_relationships=True,
    )

    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment question not found",
        )

    return question


async def _ensure_question_number_available(
    repository: AssessmentQuestionRepository,
    *,
    assessment_id: int,
    question_number: str,
    exclude_question_id: int | None = None,
) -> None:
    """
    Ensure an assessment question number is unique.
    """

    if await repository.question_number_exists(
        assessment_id=assessment_id,
        question_number=question_number,
        exclude_question_id=exclude_question_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Question number {question_number!r} "
                "is already in use in this assessment"
            ),
        )


async def _validate_section_reference(
    repository: AssessmentQuestionRepository,
    *,
    assessment_id: int,
    section_id: int | None,
) -> None:
    """
    Ensure a referenced section belongs to the same assessment.
    """

    if section_id is None:
        return

    section = await repository.get_section_by_id_and_assessment(
        section_id=section_id,
        assessment_id=assessment_id,
        include_relationships=False,
    )

    if section is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "section_id must reference a section " "belonging to this assessment"
            ),
        )


async def _validate_parent_reference(
    repository: AssessmentQuestionRepository,
    *,
    assessment_id: int,
    parent_question_id: int | None,
    question_id: int | None = None,
) -> AssessmentQuestion | None:
    """
    Validate a parent-question reference.

    The parent must belong to the same assessment and a question cannot be
    its own parent.
    """

    if parent_question_id is None:
        return None

    if question_id is not None and parent_question_id == question_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A question cannot be its own parent",
        )

    parent = await repository.get_question_by_id_and_assessment(
        question_id=parent_question_id,
        assessment_id=assessment_id,
        include_relationships=False,
    )

    if parent is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "parent_question_id must reference a question "
                "belonging to this assessment"
            ),
        )

    return parent


async def _ensure_no_parent_cycle(
    repository: AssessmentQuestionRepository,
    *,
    assessment_id: int,
    question_id: int,
    parent_question_id: int | None,
) -> None:
    """
    Ensure changing a question parent cannot create an ancestry cycle.
    """

    if parent_question_id is None:
        return

    await _validate_parent_reference(
        repository,
        assessment_id=assessment_id,
        parent_question_id=parent_question_id,
        question_id=question_id,
    )

    visited: set[int] = {
        question_id,
    }

    current_parent_id: int | None = parent_question_id

    while current_parent_id is not None:
        if current_parent_id in visited:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=("Question parent relationship would create a cycle"),
            )

        visited.add(
            current_parent_id,
        )

        parent = await repository.get_question_by_id_and_assessment(
            question_id=current_parent_id,
            assessment_id=assessment_id,
            include_relationships=False,
        )

        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Question parent hierarchy contains an invalid "
                    "assessment reference"
                ),
            )

        current_parent_id = parent.parent_question_id


def _normalise_question_type(
    question_type: AssessmentQuestionType | str,
) -> AssessmentQuestionType:
    """
    Return a validated canonical question type.

    API payloads normally arrive as ``AssessmentQuestionType`` instances, but
    service-level callers may still provide the underlying string value.
    """

    try:
        return AssessmentQuestionType(
            question_type,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported assessment question type: {question_type!r}",
        ) from exc


def _build_question_options(
    options: list[AssessmentQuestionOptionCreate] | None,
) -> list[AssessmentQuestionOption]:
    """
    Build ORM option rows from validated authoring payloads.

    Question ownership is established by the SQLAlchemy relationship when the
    returned rows are assigned to ``AssessmentQuestion.options``.
    """

    if not options:
        return []

    return [
        AssessmentQuestionOption(
            text=option.text,
            order=option.order,
            is_correct=option.is_correct,
            feedback=option.feedback,
        )
        for option in options
    ]


def _build_question_assets(
    assets: list[AssessmentQuestionAssetCreate] | None,
) -> list[AssessmentQuestionAsset]:
    """
    Build ORM asset rows from validated authoring payloads.

    ``storage_path`` remains server-side metadata. Candidate-facing schemas
    deliberately omit it, while ``candidate_visible`` determines whether a
    learner may receive the asset through an authorised delivery endpoint.
    """

    if not assets:
        return []

    return [
        AssessmentQuestionAsset(
            asset_type=(
                asset.asset_type.value
                if isinstance(
                    asset.asset_type,
                    AssessmentQuestionAssetType,
                )
                else str(
                    asset.asset_type,
                )
            ),
            storage_path=asset.storage_path,
            original_filename=asset.original_filename,
            mime_type=asset.mime_type,
            file_size_bytes=asset.file_size_bytes,
            alt_text=asset.alt_text,
            caption=asset.caption,
            order=asset.order,
            candidate_visible=asset.candidate_visible,
            source_document_id=asset.source_document_id,
            source_page_number=asset.source_page_number,
            source_bbox=asset.source_bbox,
        )
        for asset in assets
    ]


def _validate_question_configuration(
    *,
    question_type: AssessmentQuestionType,
    maximum_mark: Decimal | int | float | str,
    is_markable: bool,
    options: list[AssessmentQuestionOptionCreate],
) -> None:
    """
    Validate the complete merged interaction state for one question.

    This duplicates the important schema invariants intentionally: service
    functions are also called directly by tests and internal workflows, and a
    PATCH request must be validated *after* new values have been merged with
    the existing persisted values.
    """

    try:
        maximum_mark_decimal = Decimal(
            str(
                maximum_mark,
            ),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="maximum_mark must be a valid decimal value",
        ) from exc

    if maximum_mark_decimal < Decimal("0"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="maximum_mark cannot be negative",
        )

    option_orders = [option.order for option in options]

    if len(option_orders) != len(set(option_orders)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question option order values must be unique",
        )

    option_count = len(
        options,
    )

    correct_count = sum(1 for option in options if option.is_correct)

    if (
        question_type
        in {
            AssessmentQuestionType.WRITTEN,
            AssessmentQuestionType.NUMERIC,
            AssessmentQuestionType.STRUCTURAL,
        }
        and option_count > 0
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Written, numeric and structural questions cannot have "
                "multiple-choice options"
            ),
        )

    if question_type == AssessmentQuestionType.MULTIPLE_CHOICE_SINGLE:
        if option_count < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "A single-answer multiple-choice question must have "
                    "at least two options"
                ),
            )

        if correct_count != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "A single-answer multiple-choice question must have "
                    "exactly one correct option"
                ),
            )

    if question_type == AssessmentQuestionType.MULTIPLE_CHOICE_MULTIPLE:
        if option_count < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "A multiple-answer multiple-choice question must have "
                    "at least two options"
                ),
            )

        if correct_count < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "A multiple-answer multiple-choice question must have "
                    "at least one correct option"
                ),
            )

    if question_type == AssessmentQuestionType.TRUE_FALSE:
        if option_count != 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A true/false question must have exactly two options",
            )

        if correct_count != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A true/false question must have exactly one correct option",
            )

    if question_type == AssessmentQuestionType.STRUCTURAL:
        if is_markable:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A structural question cannot be markable",
            )

        if maximum_mark_decimal != Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A structural question must have a maximum mark of zero",
            )


def _validate_asset_orders(
    assets: list[AssessmentQuestionAssetCreate],
) -> None:
    """
    Ensure visual/resource ordering is deterministic within a question.
    """

    asset_orders = [asset.order for asset in assets]

    if len(asset_orders) != len(set(asset_orders)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question asset order values must be unique",
        )


def _options_from_existing_question(
    question: AssessmentQuestion,
) -> list[AssessmentQuestionOptionCreate]:
    """
    Convert existing ORM options into authoring payloads for merged PATCH
    validation without mutating the persisted rows.
    """

    return [
        AssessmentQuestionOptionCreate(
            text=option.text,
            order=option.order,
            is_correct=option.is_correct,
            feedback=option.feedback,
        )
        for option in question.options
    ]


def _assets_from_existing_question(
    question: AssessmentQuestion,
) -> list[AssessmentQuestionAssetCreate]:
    """
    Convert existing ORM assets into authoring payloads for PATCH replacement
    and validation.
    """

    return [
        AssessmentQuestionAssetCreate(
            asset_type=AssessmentQuestionAssetType(
                asset.asset_type,
            ),
            storage_path=asset.storage_path,
            original_filename=asset.original_filename,
            mime_type=asset.mime_type,
            file_size_bytes=asset.file_size_bytes,
            alt_text=asset.alt_text,
            caption=asset.caption,
            order=asset.order,
            candidate_visible=asset.candidate_visible,
            source_document_id=asset.source_document_id,
            source_page_number=asset.source_page_number,
            source_bbox=asset.source_bbox,
        )
        for asset in question.assets
    ]


def _translate_integrity_error(
    exc: IntegrityError,
) -> HTTPException:
    """
    Translate structural database uniqueness failures into an API conflict.

    Repository-level pre-checks provide useful messages for normal requests,
    while the database remains authoritative under concurrent writes.
    """

    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            "Assessment structure conflicts with an existing " "section or question"
        ),
    )


# ----------------------------------------------------------------------
# Section retrieval
# ----------------------------------------------------------------------


async def list_assessment_sections(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
) -> list[AssessmentSection]:
    """
    Return sections for an assessment the user may manage.
    """

    assessment = await AssessmentRepository(
        db,
    ).get_by_id(
        assessment_id,
        include_relationships=False,
    )

    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )

    await _ensure_assessment_management_access(
        db,
        current_user,
        assessment,
    )

    return await AssessmentQuestionRepository(
        db,
    ).list_sections_by_assessment(
        assessment_id,
        include_relationships=True,
    )


async def get_assessment_section(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    section_id: int,
) -> AssessmentSection:
    """
    Return one section for an assessment the user may manage.
    """

    assessment = await AssessmentRepository(
        db,
    ).get_by_id(
        assessment_id,
        include_relationships=False,
    )

    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )

    await _ensure_assessment_management_access(
        db,
        current_user,
        assessment,
    )

    return await _get_section_or_404(
        db,
        assessment_id=assessment_id,
        section_id=section_id,
    )


# ----------------------------------------------------------------------
# Section mutations
# ----------------------------------------------------------------------


async def create_assessment_section(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    *,
    title: str,
    description: str | None = None,
    order: int = 1,
    is_optional: bool = False,
) -> AssessmentSection:
    """
    Create a section in a draft assessment.
    """

    await _get_manageable_draft_assessment(
        db,
        current_user,
        assessment_id,
    )

    repository = AssessmentQuestionRepository(
        db,
    )

    await _ensure_section_order_available(
        repository,
        assessment_id=assessment_id,
        order=order,
    )

    section = AssessmentSection(
        assessment_id=assessment_id,
        title=title,
        description=description,
        order=order,
        is_optional=is_optional,
    )

    try:
        section = await repository.create_section(
            section,
        )

        await db.commit()

        await db.refresh(
            section,
        )

    except IntegrityError as exc:
        await db.rollback()

        raise _translate_integrity_error(
            exc,
        ) from exc

    except Exception:
        await db.rollback()
        raise

    return section


async def update_assessment_section(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    section_id: int,
    *,
    title: str | None = None,
    description: str | None = None,
    order: int | None = None,
    is_optional: bool | None = None,
    update_description: bool = False,
) -> AssessmentSection:
    """
    Update a section in a draft assessment.

    ``update_description`` distinguishes an omitted PATCH field from an
    explicit null value. When true, ``None`` deliberately clears the section
    description.
    """

    await _get_manageable_draft_assessment(
        db,
        current_user,
        assessment_id,
    )

    repository = AssessmentQuestionRepository(
        db,
    )

    section = await _get_section_or_404(
        db,
        assessment_id=assessment_id,
        section_id=section_id,
    )

    if order is not None:
        await _ensure_section_order_available(
            repository,
            assessment_id=assessment_id,
            order=order,
            exclude_section_id=section.id,
        )

        section.order = order

    if title is not None:
        section.title = title

    if update_description:
        section.description = description

    if is_optional is not None:
        section.is_optional = is_optional

    try:
        section = await repository.save_section(
            section,
        )

        await db.commit()

        await db.refresh(
            section,
        )

    except IntegrityError as exc:
        await db.rollback()

        raise _translate_integrity_error(
            exc,
        ) from exc

    except Exception:
        await db.rollback()
        raise

    return section


async def delete_assessment_section(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    section_id: int,
) -> Assessment:
    """
    Delete a section from a draft assessment.

    Questions assigned to the section remain part of the assessment and become
    unsectioned according to the model's SET NULL foreign-key behaviour.
    """

    await _get_manageable_draft_assessment(
        db,
        current_user,
        assessment_id,
    )

    section = await _get_section_or_404(
        db,
        assessment_id=assessment_id,
        section_id=section_id,
    )

    repository = AssessmentQuestionRepository(
        db,
    )

    try:
        await repository.delete_section(
            section,
        )

        await db.commit()

    except Exception:
        await db.rollback()
        raise

    return await _reload_assessment(
        db,
        assessment_id,
    )


# ----------------------------------------------------------------------
# Question retrieval
# ----------------------------------------------------------------------


async def list_assessment_questions(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
) -> list[AssessmentQuestion]:
    """
    Return questions for an assessment the user may manage.
    """

    assessment = await AssessmentRepository(
        db,
    ).get_by_id(
        assessment_id,
        include_relationships=False,
    )

    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )

    await _ensure_assessment_management_access(
        db,
        current_user,
        assessment,
    )

    return await AssessmentQuestionRepository(
        db,
    ).list_questions_by_assessment(
        assessment_id,
        include_relationships=True,
    )


async def get_assessment_question(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    question_id: int,
) -> AssessmentQuestion:
    """
    Return one question for an assessment the user may manage.
    """

    assessment = await AssessmentRepository(
        db,
    ).get_by_id(
        assessment_id,
        include_relationships=False,
    )

    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )

    await _ensure_assessment_management_access(
        db,
        current_user,
        assessment,
    )

    return await _get_question_or_404(
        db,
        assessment_id=assessment_id,
        question_id=question_id,
    )


# ----------------------------------------------------------------------
# Question mutations
# ----------------------------------------------------------------------


async def create_assessment_question(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    *,
    question_number: str,
    maximum_mark: Decimal | int | float | str,
    section_id: int | None = None,
    parent_question_id: int | None = None,
    title: str | None = None,
    prompt: str | None = None,
    question_type: AssessmentQuestionType | str = AssessmentQuestionType.WRITTEN,
    order: int = 1,
    is_markable: bool = True,
    options: list[AssessmentQuestionOptionCreate] | None = None,
    assets: list[AssessmentQuestionAssetCreate] | None = None,
) -> AssessmentQuestion:
    """
    Create a canonical question in a draft assessment.

    Multiple-choice options and candidate-visible visual assets are persisted
    in the same database transaction as the question so callers cannot observe
    a partially created question definition.
    """

    await _get_manageable_draft_assessment(
        db,
        current_user,
        assessment_id,
    )

    repository = AssessmentQuestionRepository(
        db,
    )

    await _ensure_question_number_available(
        repository,
        assessment_id=assessment_id,
        question_number=question_number,
    )

    await _validate_section_reference(
        repository,
        assessment_id=assessment_id,
        section_id=section_id,
    )

    await _validate_parent_reference(
        repository,
        assessment_id=assessment_id,
        parent_question_id=parent_question_id,
    )

    normalised_question_type = _normalise_question_type(
        question_type,
    )

    option_payloads = list(
        options or [],
    )

    asset_payloads = list(
        assets or [],
    )

    _validate_question_configuration(
        question_type=normalised_question_type,
        maximum_mark=maximum_mark,
        is_markable=is_markable,
        options=option_payloads,
    )

    _validate_asset_orders(
        asset_payloads,
    )

    question = AssessmentQuestion(
        assessment_id=assessment_id,
        section_id=section_id,
        parent_question_id=parent_question_id,
        question_number=question_number,
        title=title,
        prompt=prompt,
        question_type=normalised_question_type.value,
        maximum_mark=maximum_mark,
        order=order,
        is_markable=is_markable,
        options=_build_question_options(
            option_payloads,
        ),
        assets=_build_question_assets(
            asset_payloads,
        ),
    )

    try:
        question = await repository.create_question(
            question,
        )

        await db.commit()

        await db.refresh(
            question,
            attribute_names=[
                "options",
                "assets",
            ],
        )

    except IntegrityError as exc:
        await db.rollback()

        raise _translate_integrity_error(
            exc,
        ) from exc

    except Exception:
        await db.rollback()
        raise

    return question


async def update_assessment_question(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    question_id: int,
    *,
    question_number: str | None = None,
    maximum_mark: Decimal | int | float | str | None = None,
    section_id: int | None = None,
    parent_question_id: int | None = None,
    title: str | None = None,
    prompt: str | None = None,
    question_type: AssessmentQuestionType | str | None = None,
    order: int | None = None,
    is_markable: bool | None = None,
    options: list[AssessmentQuestionOptionCreate] | None = None,
    assets: list[AssessmentQuestionAssetCreate] | None = None,
    update_section: bool = False,
    update_parent: bool = False,
    update_title: bool = False,
    update_prompt: bool = False,
    update_question_type: bool = False,
    update_options: bool = False,
    update_assets: bool = False,
) -> AssessmentQuestion:
    """
    Update a canonical question in a draft assessment.

    Explicit update flags distinguish omitted PATCH fields from fields supplied
    as null.

    This allows clients to:

    - remove a section relationship with ``section_id=null``;
    - remove a parent relationship with ``parent_question_id=null``;
    - clear a nullable title with ``title=null``;
    - clear a nullable prompt with ``prompt=null``;
    - replace all structured options atomically, including with an empty list;
    - replace all visual assets atomically, including with an empty list;

    while omitted fields remain unchanged.

    Interaction-specific rules are checked against the *merged* final state.
    This prevents, for example, converting an MCQ to ``written`` while silently
    leaving old option rows attached.
    """

    await _get_manageable_draft_assessment(
        db,
        current_user,
        assessment_id,
    )

    repository = AssessmentQuestionRepository(
        db,
    )

    question = await _get_question_or_404(
        db,
        assessment_id=assessment_id,
        question_id=question_id,
    )

    if question_number is not None:
        await _ensure_question_number_available(
            repository,
            assessment_id=assessment_id,
            question_number=question_number,
            exclude_question_id=question.id,
        )

        question.question_number = question_number

    if update_section:
        await _validate_section_reference(
            repository,
            assessment_id=assessment_id,
            section_id=section_id,
        )

        question.section_id = section_id

    if update_parent:
        await _ensure_no_parent_cycle(
            repository,
            assessment_id=assessment_id,
            question_id=question.id,
            parent_question_id=parent_question_id,
        )

        question.parent_question_id = parent_question_id

    if update_title:
        question.title = title

    if update_prompt:
        question.prompt = prompt

    final_question_type = _normalise_question_type(
        (
            question_type
            if update_question_type and question_type is not None
            else question.question_type
        ),
    )

    final_maximum_mark: Decimal | int | float | str = (
        maximum_mark if maximum_mark is not None else question.maximum_mark
    )

    final_is_markable = is_markable if is_markable is not None else question.is_markable

    final_options = (
        list(
            options or [],
        )
        if update_options
        else _options_from_existing_question(
            question,
        )
    )

    final_assets = (
        list(
            assets or [],
        )
        if update_assets
        else _assets_from_existing_question(
            question,
        )
    )

    _validate_question_configuration(
        question_type=final_question_type,
        maximum_mark=final_maximum_mark,
        is_markable=final_is_markable,
        options=final_options,
    )

    _validate_asset_orders(
        final_assets,
    )

    if update_question_type:
        if question_type is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="question_type cannot be null",
            )

        question.question_type = final_question_type.value

    if maximum_mark is not None:
        question.maximum_mark = maximum_mark

    if order is not None:
        question.order = order

    if is_markable is not None:
        question.is_markable = is_markable

    if update_options:
        question.options = _build_question_options(
            final_options,
        )

    if update_assets:
        question.assets = _build_question_assets(
            final_assets,
        )

    try:
        question = await repository.save_question(
            question,
        )

        await db.commit()

        await db.refresh(
            question,
            attribute_names=[
                "options",
                "assets",
            ],
        )

    except IntegrityError as exc:
        await db.rollback()

        raise _translate_integrity_error(
            exc,
        ) from exc

    except Exception:
        await db.rollback()
        raise

    return question


async def delete_assessment_question(
    db: AsyncSession,
    current_user: User,
    assessment_id: int,
    question_id: int,
) -> Assessment:
    """
    Delete a question from a draft assessment.

    Child questions are removed through the configured ORM/database cascade.
    """

    await _get_manageable_draft_assessment(
        db,
        current_user,
        assessment_id,
    )

    question = await _get_question_or_404(
        db,
        assessment_id=assessment_id,
        question_id=question_id,
    )

    repository = AssessmentQuestionRepository(
        db,
    )

    try:
        await repository.delete_question(
            question,
        )

        await db.commit()

    except Exception:
        await db.rollback()
        raise

    return await _reload_assessment(
        db,
        assessment_id,
    )
