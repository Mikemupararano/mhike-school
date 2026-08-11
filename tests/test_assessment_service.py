from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.assessment import AssessmentStatus
from app.models.assessment_question import AssessmentQuestion
from app.models.course import Course
from app.models.user import UserRole
from app.services.assessment_service import (
    archive_assessment,
    close_assessment,
    create_assessment,
    delete_assessment,
    get_assessment,
    list_assessments,
    publish_assessment,
    transition_assessment_status,
    update_assessment,
)
from tests.conftest import create_test_user


async def _create_course(
    db_session,
    *,
    teacher_id: int,
    school_id: int,
    title: str = "Assessment Test Course",
) -> Course:
    """
    Create and persist a minimal course suitable for assessment tests.
    """

    course = Course(
        title=title,
        description="Course used by assessment service tests.",
        teacher_id=teacher_id,
        school_id=school_id,
        published=True,
    )

    db_session.add(course)
    await db_session.flush()

    return course


async def _create_assessment_for_teacher(
    db_session,
    teacher_user,
    *,
    title: str = "Physics Assessment",
):
    """
    Create a course and draft assessment owned by the supplied teacher.
    """

    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
    )

    assessment = await create_assessment(
        db=db_session,
        current_user=teacher_user,
        course_id=course.id,
        title=title,
        description="Assessment service test.",
        assessment_type="test",
        academic_year="2026/27",
        term="Autumn",
    )

    return course, assessment


async def _add_markable_question(
    db_session,
    assessment_id: int,
    *,
    question_number: str = "1",
    maximum_mark: Decimal = Decimal("10.00"),
    order: int = 1,
) -> AssessmentQuestion:
    """
    Add and persist a markable question to an assessment.

    The helper deliberately does not expire the whole AsyncSession.
    Expiring all ORM state would make later synchronous attribute access,
    such as ``assessment.id``, attempt asynchronous database I/O and raise
    SQLAlchemy MissingGreenlet errors.
    """

    question = AssessmentQuestion(
        assessment_id=assessment_id,
        question_number=question_number,
        prompt="Test question",
        maximum_mark=maximum_mark,
        order=order,
        is_markable=True,
    )

    db_session.add(question)
    await db_session.commit()
    await db_session.refresh(question)

    return question


@pytest.mark.asyncio
async def test_teacher_can_create_assessment_for_own_course(
    db_session,
    teacher_user,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
    )

    assessment = await create_assessment(
        db=db_session,
        current_user=teacher_user,
        course_id=course.id,
        title="Mechanics Test",
        description="Forces and motion.",
        assessment_type="class_test",
        academic_year="2026/27",
        term="Autumn",
        anonymous_marking=True,
    )

    assert assessment.id is not None
    assert assessment.school_id == teacher_user.school_id
    assert assessment.course_id == course.id
    assert assessment.created_by_id == teacher_user.id
    assert assessment.title == "Mechanics Test"
    assert assessment.status == AssessmentStatus.DRAFT
    assert assessment.anonymous_marking is True


@pytest.mark.asyncio
async def test_teacher_cannot_create_assessment_for_another_teachers_course(
    db_session,
    teacher_user,
):
    other_teacher = await create_test_user(
        db_session,
        email="assessment.other.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    course = await _create_course(
        db_session,
        teacher_id=other_teacher.id,
        school_id=other_teacher.school_id,
        title="Other Teacher Course",
    )

    with pytest.raises(HTTPException) as exc:
        await create_assessment(
            db=db_session,
            current_user=teacher_user,
            course_id=course.id,
            title="Forbidden Assessment",
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_create_assessment_rejects_invalid_date_window(
    db_session,
    teacher_user,
):
    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
    )

    scheduled_at = datetime(
        2026,
        9,
        10,
        10,
        0,
        tzinfo=timezone.utc,
    )

    closes_at = datetime(
        2026,
        9,
        10,
        9,
        0,
        tzinfo=timezone.utc,
    )

    with pytest.raises(HTTPException) as exc:
        await create_assessment(
            db=db_session,
            current_user=teacher_user,
            course_id=course.id,
            title="Invalid Date Assessment",
            scheduled_at=scheduled_at,
            closes_at=closes_at,
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_teacher_can_get_own_course_assessment(
    db_session,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    loaded = await get_assessment(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
    )

    assert loaded.id == assessment.id
    assert loaded.title == assessment.title


@pytest.mark.asyncio
async def test_teacher_cannot_get_other_teachers_assessment(
    db_session,
    teacher_user,
):
    other_teacher = await create_test_user(
        db_session,
        email="assessment.owner@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    course = await _create_course(
        db_session,
        teacher_id=other_teacher.id,
        school_id=other_teacher.school_id,
    )

    assessment = await create_assessment(
        db=db_session,
        current_user=other_teacher,
        course_id=course.id,
        title="Other Teacher Assessment",
    )

    with pytest.raises(HTTPException) as exc:
        await get_assessment(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_teacher_lists_only_assessments_created_by_teacher(
    db_session,
    teacher_user,
):
    _, own_assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        title="Teacher Assessment",
    )

    other_teacher = await create_test_user(
        db_session,
        email="assessment.list.other@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    other_course = await _create_course(
        db_session,
        teacher_id=other_teacher.id,
        school_id=other_teacher.school_id,
        title="Other Course",
    )

    other_assessment = await create_assessment(
        db=db_session,
        current_user=other_teacher,
        course_id=other_course.id,
        title="Other Assessment",
    )

    assessments = await list_assessments(
        db=db_session,
        current_user=teacher_user,
    )

    assessment_ids = {assessment.id for assessment in assessments}

    assert own_assessment.id in assessment_ids
    assert other_assessment.id not in assessment_ids


@pytest.mark.asyncio
async def test_teacher_can_update_draft_assessment(
    db_session,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    updated = await update_assessment(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        title="Updated Physics Assessment",
        description="Updated description.",
        assessment_type="mock",
        academic_year="2026/27",
        term="Spring",
        anonymous_marking=True,
    )

    assert updated.title == "Updated Physics Assessment"
    assert updated.description == "Updated description."
    assert updated.assessment_type == "mock"
    assert updated.academic_year == "2026/27"
    assert updated.term == "Spring"
    assert updated.anonymous_marking is True


@pytest.mark.asyncio
async def test_cannot_publish_assessment_without_questions(
    db_session,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    with pytest.raises(HTTPException) as exc:
        await publish_assessment(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_cannot_publish_assessment_with_zero_mark_question(
    db_session,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    await _add_markable_question(
        db_session,
        assessment.id,
        maximum_mark=Decimal("0.00"),
    )

    with pytest.raises(HTTPException) as exc:
        await publish_assessment(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_teacher_can_publish_valid_assessment(
    db_session,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    await _add_markable_question(
        db_session,
        assessment.id,
        maximum_mark=Decimal("10.00"),
    )

    published = await publish_assessment(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
    )

    assert published.status == AssessmentStatus.PUBLISHED


@pytest.mark.asyncio
async def test_published_assessment_cannot_be_edited(
    db_session,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    await _add_markable_question(
        db_session,
        assessment.id,
    )

    await publish_assessment(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
    )

    with pytest.raises(HTTPException) as exc:
        await update_assessment(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            title="Should Not Change",
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_published_assessment_can_be_closed(
    db_session,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    await _add_markable_question(
        db_session,
        assessment.id,
    )

    await publish_assessment(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
    )

    closed = await close_assessment(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
    )

    assert closed.status == AssessmentStatus.CLOSED


@pytest.mark.asyncio
async def test_closed_assessment_can_be_archived(
    db_session,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    await _add_markable_question(
        db_session,
        assessment.id,
    )

    await publish_assessment(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
    )

    await close_assessment(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
    )

    archived = await archive_assessment(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
    )

    assert archived.status == AssessmentStatus.ARCHIVED


@pytest.mark.asyncio
async def test_invalid_status_transition_is_rejected(
    db_session,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    with pytest.raises(HTTPException) as exc:
        await transition_assessment_status(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            new_status=AssessmentStatus.CLOSED,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_invalid_status_value_is_rejected(
    db_session,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    with pytest.raises(HTTPException) as exc:
        await transition_assessment_status(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            new_status="not-a-real-status",
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_draft_assessment_can_be_deleted(
    db_session,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    assessment_id = assessment.id

    await delete_assessment(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment_id,
    )

    with pytest.raises(HTTPException) as exc:
        await get_assessment(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment_id,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_published_assessment_cannot_be_deleted(
    db_session,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    await _add_markable_question(
        db_session,
        assessment.id,
    )

    await publish_assessment(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
    )

    with pytest.raises(HTTPException) as exc:
        await delete_assessment(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
        )

    assert exc.value.status_code == 409
