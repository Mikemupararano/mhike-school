from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus
from app.models.assessment_candidate import (
    AssessmentCandidate,
    AssessmentCandidateStatus,
)
from app.models.course import Course
from app.models.user import UserRole
from app.repositories.assessment_candidate_bulk import (
    AssessmentCandidateBulkRepository,
)
from tests.conftest import create_test_user


async def _create_assessment(
    db_session: AsyncSession,
    *,
    teacher_user,
    title: str = "Bulk Candidate Repository Assessment",
) -> Assessment:
    """
    Create a persisted assessment for repository tests.
    """

    course = Course(
        title=f"{title} Course",
        description="Course used by bulk candidate repository tests.",
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        published=True,
    )

    db_session.add(
        course,
    )
    await db_session.commit()
    await db_session.refresh(
        course,
    )

    assessment = Assessment(
        school_id=teacher_user.school_id,
        course_id=course.id,
        created_by_id=teacher_user.id,
        title=title,
        description="Bulk candidate repository test.",
        assessment_type="test",
        academic_year="2026/27",
        term="Autumn",
        status=AssessmentStatus.DRAFT,
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
    Create a student in the supplied school.
    """

    return await create_test_user(
        db_session,
        email=email,
        roles=[
            UserRole.STUDENT,
        ],
        school_id=school_id,
    )


@pytest.mark.asyncio
async def test_get_existing_student_ids_returns_only_matching_allocations(
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
        email="bulk.repo.existing.first@example.com",
    )
    second_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.repo.existing.second@example.com",
    )
    third_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.repo.existing.third@example.com",
    )

    db_session.add_all(
        [
            AssessmentCandidate(
                assessment_id=assessment.id,
                student_id=first_student.id,
                status=AssessmentCandidateStatus.ALLOCATED,
            ),
            AssessmentCandidate(
                assessment_id=assessment.id,
                student_id=third_student.id,
                status=AssessmentCandidateStatus.ALLOCATED,
            ),
        ],
    )
    await db_session.commit()

    repository = AssessmentCandidateBulkRepository(
        db_session,
    )

    existing = await repository.get_existing_student_ids(
        assessment_id=assessment.id,
        student_ids=[
            first_student.id,
            second_student.id,
            third_student.id,
        ],
    )

    assert existing == {
        first_student.id,
        third_student.id,
    }


@pytest.mark.asyncio
async def test_get_existing_student_ids_is_assessment_scoped(
    db_session: AsyncSession,
    teacher_user,
) -> None:
    first_assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
        title="First Bulk Assessment",
    )
    second_assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
        title="Second Bulk Assessment",
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.repo.assessment.scope@example.com",
    )

    db_session.add(
        AssessmentCandidate(
            assessment_id=first_assessment.id,
            student_id=student.id,
            status=AssessmentCandidateStatus.ALLOCATED,
        ),
    )
    await db_session.commit()

    repository = AssessmentCandidateBulkRepository(
        db_session,
    )

    existing = await repository.get_existing_student_ids(
        assessment_id=second_assessment.id,
        student_ids=[
            student.id,
        ],
    )

    assert existing == set()


@pytest.mark.asyncio
async def test_get_existing_student_ids_deduplicates_input(
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
        email="bulk.repo.deduplicate@example.com",
    )

    db_session.add(
        AssessmentCandidate(
            assessment_id=assessment.id,
            student_id=student.id,
            status=AssessmentCandidateStatus.ALLOCATED,
        ),
    )
    await db_session.commit()

    repository = AssessmentCandidateBulkRepository(
        db_session,
    )

    existing = await repository.get_existing_student_ids(
        assessment_id=assessment.id,
        student_ids=[
            student.id,
            student.id,
            student.id,
        ],
    )

    assert existing == {
        student.id,
    }


@pytest.mark.asyncio
async def test_get_existing_student_ids_accepts_empty_collection(
    db_session: AsyncSession,
    teacher_user,
) -> None:
    assessment = await _create_assessment(
        db_session,
        teacher_user=teacher_user,
    )

    repository = AssessmentCandidateBulkRepository(
        db_session,
    )

    existing = await repository.get_existing_student_ids(
        assessment_id=assessment.id,
        student_ids=[],
    )

    assert existing == set()


@pytest.mark.asyncio
async def test_get_existing_student_ids_rejects_invalid_assessment_id(
    db_session: AsyncSession,
) -> None:
    repository = AssessmentCandidateBulkRepository(
        db_session,
    )

    with pytest.raises(
        ValueError,
        match="assessment_id must be a positive integer",
    ):
        await repository.get_existing_student_ids(
            assessment_id=0,
            student_ids=[],
        )


@pytest.mark.asyncio
async def test_get_existing_student_ids_rejects_invalid_student_id(
    db_session: AsyncSession,
) -> None:
    repository = AssessmentCandidateBulkRepository(
        db_session,
    )

    with pytest.raises(
        ValueError,
        match="student_id must be a positive integer",
    ):
        await repository.get_existing_student_ids(
            assessment_id=1,
            student_ids=[
                0,
            ],
        )


@pytest.mark.asyncio
async def test_get_existing_student_ids_rejects_boolean_student_id(
    db_session: AsyncSession,
) -> None:
    repository = AssessmentCandidateBulkRepository(
        db_session,
    )

    with pytest.raises(
        ValueError,
        match="student_id must be a positive integer",
    ):
        await repository.get_existing_student_ids(
            assessment_id=1,
            student_ids=[
                True,
            ],
        )


@pytest.mark.asyncio
async def test_create_candidates_persists_batch_after_caller_commit(
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
        email="bulk.repo.create.first@example.com",
    )
    second_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="bulk.repo.create.second@example.com",
    )

    repository = AssessmentCandidateBulkRepository(
        db_session,
    )

    created = await repository.create_candidates(
        [
            AssessmentCandidate(
                assessment_id=assessment.id,
                student_id=first_student.id,
                status=AssessmentCandidateStatus.ALLOCATED,
            ),
            AssessmentCandidate(
                assessment_id=assessment.id,
                student_id=second_student.id,
                status=AssessmentCandidateStatus.ALLOCATED,
            ),
        ],
    )

    assert len(created) == 2
    assert all(candidate.id is not None for candidate in created)

    await db_session.commit()

    result = await db_session.execute(
        select(
            AssessmentCandidate,
        ).where(
            AssessmentCandidate.assessment_id == assessment.id,
        ),
    )

    persisted = list(
        result.scalars().all(),
    )

    assert {candidate.student_id for candidate in persisted} == {
        first_student.id,
        second_student.id,
    }


@pytest.mark.asyncio
async def test_create_candidates_does_not_commit_transaction(
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
        email="bulk.repo.no.commit@example.com",
    )

    # Preserve scalar identifiers before rollback. SQLAlchemy expires ORM
    # instances on rollback, and accessing expired attributes afterwards can
    # attempt asynchronous database I/O outside the expected greenlet context.
    assessment_id = assessment.id
    student_id = student.id

    repository = AssessmentCandidateBulkRepository(
        db_session,
    )

    await repository.create_candidates(
        [
            AssessmentCandidate(
                assessment_id=assessment_id,
                student_id=student_id,
                status=AssessmentCandidateStatus.ALLOCATED,
            ),
        ],
    )

    await db_session.rollback()

    result = await db_session.execute(
        select(
            AssessmentCandidate,
        ).where(
            AssessmentCandidate.assessment_id == assessment_id,
            AssessmentCandidate.student_id == student_id,
        ),
    )

    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_create_candidates_accepts_empty_batch(
    db_session: AsyncSession,
) -> None:
    repository = AssessmentCandidateBulkRepository(
        db_session,
    )

    created = await repository.create_candidates(
        [],
    )

    assert created == []


@pytest.mark.asyncio
async def test_create_candidates_rejects_duplicate_student_in_batch(
    db_session: AsyncSession,
) -> None:
    repository = AssessmentCandidateBulkRepository(
        db_session,
    )

    candidates = [
        AssessmentCandidate(
            assessment_id=10,
            student_id=20,
            status=AssessmentCandidateStatus.ALLOCATED,
        ),
        AssessmentCandidate(
            assessment_id=10,
            student_id=20,
            status=AssessmentCandidateStatus.ALLOCATED,
        ),
    ]

    with pytest.raises(
        ValueError,
        match="duplicate student_id",
    ):
        await repository.create_candidates(
            candidates,
        )


@pytest.mark.asyncio
async def test_create_candidates_rejects_multiple_assessments(
    db_session: AsyncSession,
) -> None:
    repository = AssessmentCandidateBulkRepository(
        db_session,
    )

    candidates = [
        AssessmentCandidate(
            assessment_id=10,
            student_id=20,
            status=AssessmentCandidateStatus.ALLOCATED,
        ),
        AssessmentCandidate(
            assessment_id=11,
            student_id=21,
            status=AssessmentCandidateStatus.ALLOCATED,
        ),
    ]

    with pytest.raises(
        ValueError,
        match="same assessment",
    ):
        await repository.create_candidates(
            candidates,
        )


@pytest.mark.asyncio
async def test_create_candidates_rejects_invalid_candidate_student_id(
    db_session: AsyncSession,
) -> None:
    repository = AssessmentCandidateBulkRepository(
        db_session,
    )

    candidate = AssessmentCandidate(
        assessment_id=10,
        student_id=0,
        status=AssessmentCandidateStatus.ALLOCATED,
    )

    with pytest.raises(
        ValueError,
        match="candidate.student_id must be a positive integer",
    ):
        await repository.create_candidates(
            [
                candidate,
            ],
        )
