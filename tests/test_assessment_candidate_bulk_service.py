from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus
from app.models.assessment_candidate import AssessmentCandidate
from app.models.class_group import ClassGroup
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.user import UserRole
from app.services.assessment_candidate_bulk_service import (
    allocate_class_candidates,
    bulk_allocate_candidates,
    preview_class_candidate_allocation,
)
from tests.conftest import create_test_user


async def _create_course(
    db_session: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
    title: str = "Bulk Candidate Service Course",
) -> Course:
    """
    Create a course for bulk-allocation service tests.
    """

    course = Course(
        title=title,
        description="Bulk candidate service test course.",
        teacher_id=teacher_id,
        school_id=school_id,
        published=True,
    )

    db_session.add(
        course,
    )
    await db_session.commit()
    await db_session.refresh(
        course,
    )

    return course


async def _create_assessment(
    db_session: AsyncSession,
    *,
    teacher_user,
    title: str = "Bulk Candidate Service Assessment",
    assessment_status: AssessmentStatus = AssessmentStatus.DRAFT,
) -> Assessment:
    """
    Create a teacher-owned assessment.
    """

    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        title=f"{title} Course",
    )

    assessment = Assessment(
        school_id=teacher_user.school_id,
        course_id=course.id,
        created_by_id=teacher_user.id,
        title=title,
        description="Bulk candidate service test.",
        assessment_type="test",
        academic_year="2026/27",
        term="Autumn",
        status=assessment_status,
        anonymous_marking=False,
    )

    db_session.add(
        assessment,
    )
    await db_session.commit()
    await db_session.refresh(
        assessment,
    )

    return assessment


async def _create_student(
    db_session: AsyncSession,
    *,
    school_id: int,
    email: str,
):
    """
    Create a student in one school.
    """

    return await create_test_user(
        db_session,
        email=email,
        roles=[
            UserRole.STUDENT,
        ],
        school_id=school_id,
    )


async def _create_class(
    db_session: AsyncSession,
    *,
    school_id: int,
    name: str = "10A Physics",
) -> ClassGroup:
    """
    Create a class group.
    """

    class_group = ClassGroup(
        name=name,
        school_id=school_id,
    )

    db_session.add(
        class_group,
    )
    await db_session.commit()
    await db_session.refresh(
        class_group,
    )

    return class_group


async def _enrol_student(
    db_session: AsyncSession,
    *,
    class_id: int,
    student_id: int,
) -> Enrollment:
    """
    Enrol one student in a class.
    """

    enrollment = Enrollment(
        class_id=class_id,
        user_id=student_id,
    )

    db_session.add(
        enrollment,
    )
    await db_session.commit()
    await db_session.refresh(
        enrollment,
    )

    return enrollment


@pytest.mark.asyncio
async def test_bulk_allocate_candidates_creates_multiple_candidates(
    db_session: AsyncSession,
    teacher_user,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    first_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.service.first@example.com",
    )
    second_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.service.second@example.com",
    )

    result = await bulk_allocate_candidates(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        student_ids=[
            first_student.id,
            second_student.id,
        ],
    )

    assert result.requested_count == 2
    assert result.unique_requested_count == 2
    assert result.created_count == 2
    assert result.already_allocated_count == 0
    assert result.ineligible_count == 0

    assert {item.student_id for item in result.items if item.outcome == "created"} == {
        first_student.id,
        second_student.id,
    }


@pytest.mark.asyncio
async def test_bulk_allocate_candidates_deduplicates_requested_ids(
    db_session: AsyncSession,
    teacher_user,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.service.deduplicate@example.com",
    )

    result = await bulk_allocate_candidates(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        student_ids=[
            student.id,
            student.id,
            student.id,
        ],
    )

    assert result.requested_count == 3
    assert result.unique_requested_count == 1
    assert result.created_count == 1
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_bulk_allocate_candidates_skips_existing_allocation(
    db_session: AsyncSession,
    teacher_user,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    first_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.service.existing@example.com",
    )
    second_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.service.new@example.com",
    )

    first_result = await bulk_allocate_candidates(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        student_ids=[
            first_student.id,
        ],
    )

    assert first_result.created_count == 1

    second_result = await bulk_allocate_candidates(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        student_ids=[
            first_student.id,
            second_student.id,
        ],
    )

    assert second_result.created_count == 1
    assert second_result.already_allocated_count == 1

    outcomes = {item.student_id: item.outcome for item in second_result.items}

    assert outcomes[first_student.id] == "already_allocated"
    assert outcomes[second_student.id] == "created"


@pytest.mark.asyncio
async def test_bulk_allocate_candidates_rejects_empty_request(
    db_session: AsyncSession,
    teacher_user,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    with pytest.raises(HTTPException) as exc:
        await bulk_allocate_candidates(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            student_ids=[],
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_bulk_allocate_candidates_rejects_non_student(
    db_session: AsyncSession,
    teacher_user,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    other_teacher = await create_test_user(
        db_session,
        email="bulk.service.not.student@example.com",
        roles=[
            UserRole.TEACHER,
        ],
        school_id=teacher_user.school_id,
    )

    with pytest.raises(HTTPException) as exc:
        await bulk_allocate_candidates(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            student_ids=[
                other_teacher.id,
            ],
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_bulk_allocate_candidates_rejects_other_school_student(
    db_session: AsyncSession,
    teacher_user,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    other_school_student = await create_test_user(
        db_session,
        email="bulk.service.other.school@example.com",
        roles=[
            UserRole.STUDENT,
        ],
        school_id=None,
    )

    with pytest.raises(HTTPException) as exc:
        await bulk_allocate_candidates(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            student_ids=[
                other_school_student.id,
            ],
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_bulk_allocate_candidates_is_atomic_on_invalid_student(
    db_session: AsyncSession,
    teacher_user,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    valid_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.service.atomic.valid@example.com",
    )

    non_student = await create_test_user(
        db_session,
        email="bulk.service.atomic.invalid@example.com",
        roles=[
            UserRole.TEACHER,
        ],
        school_id=teacher_user.school_id,
    )

    with pytest.raises(HTTPException):
        await bulk_allocate_candidates(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            student_ids=[
                valid_student.id,
                non_student.id,
            ],
        )

    result = await db_session.execute(
        select(
            AssessmentCandidate,
        ).where(
            AssessmentCandidate.assessment_id == assessment.id,
        ),
    )

    assert (
        list(
            result.scalars().all(),
        )
        == []
    )


@pytest.mark.asyncio
async def test_bulk_allocate_candidates_rejects_closed_assessment(
    db_session: AsyncSession,
    teacher_user,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
        assessment_status=AssessmentStatus.CLOSED,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.service.closed@example.com",
    )

    with pytest.raises(HTTPException) as exc:
        await bulk_allocate_candidates(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            student_ids=[
                student.id,
            ],
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_allocate_class_candidates_creates_current_class_members(
    db_session: AsyncSession,
    teacher_user,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    class_group = await _create_class(
        db_session,
        school_id=teacher_user.school_id,
    )

    first_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.class.first@example.com",
    )
    second_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.class.second@example.com",
    )

    await _enrol_student(
        db_session,
        class_id=class_group.id,
        student_id=first_student.id,
    )
    await _enrol_student(
        db_session,
        class_id=class_group.id,
        student_id=second_student.id,
    )

    result = await allocate_class_candidates(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        class_id=class_group.id,
    )

    assert result.source == "class"
    assert result.class_id == class_group.id
    assert result.requested_count == 2
    assert result.created_count == 2
    assert result.already_allocated_count == 0


@pytest.mark.asyncio
async def test_allocate_class_candidates_is_idempotent(
    db_session: AsyncSession,
    teacher_user,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    class_group = await _create_class(
        db_session,
        school_id=teacher_user.school_id,
        name="10B Physics",
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.class.idempotent@example.com",
    )

    await _enrol_student(
        db_session,
        class_id=class_group.id,
        student_id=student.id,
    )

    first = await allocate_class_candidates(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        class_id=class_group.id,
    )

    second = await allocate_class_candidates(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        class_id=class_group.id,
    )

    assert first.created_count == 1
    assert second.created_count == 0
    assert second.already_allocated_count == 1


@pytest.mark.asyncio
async def test_allocate_empty_class_is_safe_noop(
    db_session: AsyncSession,
    teacher_user,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    class_group = await _create_class(
        db_session,
        school_id=teacher_user.school_id,
        name="Empty Class",
    )

    result = await allocate_class_candidates(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        class_id=class_group.id,
    )

    assert result.requested_count == 0
    assert result.unique_requested_count == 0
    assert result.created_count == 0
    assert result.items == ()


@pytest.mark.asyncio
async def test_allocate_class_candidates_rejects_unknown_class(
    db_session: AsyncSession,
    teacher_user,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    with pytest.raises(HTTPException) as exc:
        await allocate_class_candidates(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            class_id=999999,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_preview_class_candidate_allocation_reports_eligibility(
    db_session: AsyncSession,
    teacher_user,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    class_group = await _create_class(
        db_session,
        school_id=teacher_user.school_id,
        name="Preview Class",
    )

    allocated_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.preview.allocated@example.com",
    )
    eligible_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.preview.eligible@example.com",
    )

    await _enrol_student(
        db_session,
        class_id=class_group.id,
        student_id=allocated_student.id,
    )
    await _enrol_student(
        db_session,
        class_id=class_group.id,
        student_id=eligible_student.id,
    )

    await bulk_allocate_candidates(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        student_ids=[
            allocated_student.id,
        ],
    )

    preview = await preview_class_candidate_allocation(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        class_id=class_group.id,
    )

    assert preview.allocation_allowed is True
    assert preview.enrolled_count == 2
    assert preview.student_count == 2
    assert preview.eligible_count == 1
    assert preview.already_allocated_count == 1

    assert preview.eligible_student_ids == (eligible_student.id,)
    assert preview.already_allocated_student_ids == (allocated_student.id,)


@pytest.mark.asyncio
async def test_preview_closed_assessment_is_read_only_and_not_allocatable(
    db_session: AsyncSession,
    teacher_user,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
        assessment_status=AssessmentStatus.CLOSED,
    )

    class_group = await _create_class(
        db_session,
        school_id=teacher_user.school_id,
        name="Closed Preview Class",
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.preview.closed@example.com",
    )

    await _enrol_student(
        db_session,
        class_id=class_group.id,
        student_id=student.id,
    )

    preview = await preview_class_candidate_allocation(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        class_id=class_group.id,
    )

    assert preview.allocation_allowed is False
    assert preview.eligible_count == 1

    result = await db_session.execute(
        select(
            AssessmentCandidate,
        ).where(
            AssessmentCandidate.assessment_id == assessment.id,
        ),
    )

    assert (
        list(
            result.scalars().all(),
        )
        == []
    )
