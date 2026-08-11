from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentStatus
from app.models.assessment_candidate import (
    AssessmentCandidateStatus,
    AssessmentScriptStatus,
)
from app.models.assessment_question import AssessmentQuestion
from app.models.course import Course
from app.models.user import UserRole
from app.services.assessment_candidate_service import (
    allocate_candidate,
    create_script_version,
    delete_candidate,
    delete_script,
    finalise_script,
    get_candidate,
    get_script,
    list_assessment_candidates,
    list_candidate_scripts,
    mark_candidate_absent,
    mark_script_complete,
    send_script_to_moderation,
    start_candidate,
    start_script_marking,
    submit_candidate,
    submit_script,
    transition_candidate_status,
    transition_script_status,
    update_candidate_details,
    withdraw_candidate,
)
from tests.conftest import create_test_user


async def _create_course(
    db_session: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
    title: str = "Assessment Candidate Test Course",
) -> Course:
    """
    Create and persist a minimal course for candidate-service tests.
    """

    course = Course(
        title=title,
        description="Course used by assessment candidate service tests.",
        teacher_id=teacher_id,
        school_id=school_id,
        published=True,
    )

    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)

    return course


async def _create_assessment(
    db_session: AsyncSession,
    *,
    teacher_id: int,
    school_id: int,
    course_id: int,
    title: str = "Candidate Test Assessment",
    assessment_status: AssessmentStatus = AssessmentStatus.DRAFT,
) -> Assessment:
    """
    Create and persist an assessment.
    """

    assessment = Assessment(
        school_id=school_id,
        course_id=course_id,
        created_by_id=teacher_id,
        title=title,
        description="Assessment candidate service test.",
        assessment_type="test",
        academic_year="2026/27",
        term="Autumn",
        status=assessment_status,
        anonymous_marking=False,
    )

    db_session.add(assessment)
    await db_session.commit()
    await db_session.refresh(assessment)

    return assessment


async def _create_assessment_for_teacher(
    db_session: AsyncSession,
    teacher_user,
    *,
    title: str = "Candidate Test Assessment",
    assessment_status: AssessmentStatus = AssessmentStatus.DRAFT,
) -> tuple[Course, Assessment]:
    """
    Create a teacher-owned course and assessment.
    """

    course = await _create_course(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
    )

    assessment = await _create_assessment(
        db_session,
        teacher_id=teacher_user.id,
        school_id=teacher_user.school_id,
        course_id=course.id,
        title=title,
        assessment_status=assessment_status,
    )

    return course, assessment


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
        roles=[UserRole.STUDENT],
        school_id=school_id,
    )


async def _add_markable_question(
    db_session: AsyncSession,
    *,
    assessment_id: int,
    maximum_mark: Decimal = Decimal("10.00"),
) -> AssessmentQuestion:
    """
    Add one markable question.
    """

    question = AssessmentQuestion(
        assessment_id=assessment_id,
        question_number="1",
        prompt="Test question",
        maximum_mark=maximum_mark,
        order=1,
        is_markable=True,
    )

    db_session.add(question)
    await db_session.commit()
    await db_session.refresh(question)

    return question


async def _allocate_test_candidate(
    db_session: AsyncSession,
    *,
    teacher_user,
    assessment: Assessment,
    student,
):
    """
    Allocate a student using the production service.
    """

    return await allocate_candidate(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        student_id=student.id,
        candidate_number="CAND-001",
        access_arrangements="25% extra time",
    )


# ----------------------------------------------------------------------
# Candidate allocation
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_allocate_student_to_own_assessment(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.allocate.student@example.com",
    )

    candidate = await allocate_candidate(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        student_id=student.id,
        candidate_number="P001",
        access_arrangements="Reader",
    )

    assert candidate.id is not None
    assert candidate.assessment_id == assessment.id
    assert candidate.student_id == student.id
    assert candidate.status == AssessmentCandidateStatus.ALLOCATED
    assert candidate.candidate_number == "P001"
    assert candidate.access_arrangements == "Reader"


@pytest.mark.asyncio
async def test_duplicate_candidate_allocation_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.duplicate.student@example.com",
    )

    await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    with pytest.raises(HTTPException) as exc:
        await allocate_candidate(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            student_id=student.id,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_non_student_cannot_be_allocated(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    other_teacher = await create_test_user(
        db_session,
        email="candidate.not.student@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    with pytest.raises(HTTPException) as exc:
        await allocate_candidate(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            student_id=other_teacher.id,
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_student_from_other_school_cannot_be_allocated(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    other_school_student = await create_test_user(
        db_session,
        email="candidate.other.school.student@example.com",
        roles=[UserRole.STUDENT],
        school_id=None,
    )

    with pytest.raises(HTTPException) as exc:
        await allocate_candidate(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            student_id=other_school_student.id,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_teacher_cannot_allocate_to_other_teachers_assessment(
    db_session: AsyncSession,
    teacher_user,
):
    other_teacher = await create_test_user(
        db_session,
        email="candidate.other.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    course = await _create_course(
        db_session,
        teacher_id=other_teacher.id,
        school_id=other_teacher.school_id,
        title="Other Teacher Course",
    )

    assessment = await _create_assessment(
        db_session,
        teacher_id=other_teacher.id,
        school_id=other_teacher.school_id,
        course_id=course.id,
        title="Other Teacher Assessment",
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.other.teacher.student@example.com",
    )

    with pytest.raises(HTTPException) as exc:
        await allocate_candidate(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            student_id=student.id,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_closed_assessment_rejects_new_candidate(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        assessment_status=AssessmentStatus.CLOSED,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.closed.student@example.com",
    )

    with pytest.raises(HTTPException) as exc:
        await allocate_candidate(
            db=db_session,
            current_user=teacher_user,
            assessment_id=assessment.id,
            student_id=student.id,
        )

    assert exc.value.status_code == 409


# ----------------------------------------------------------------------
# Candidate retrieval and metadata
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_get_candidate(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.get.student@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    loaded = await get_candidate(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    assert loaded.id == candidate.id
    assert loaded.student_id == student.id
    assert loaded.assessment_id == assessment.id


@pytest.mark.asyncio
async def test_teacher_can_list_assessment_candidates(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    first_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.list.first@example.com",
    )

    second_student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.list.second@example.com",
    )

    first_candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=first_student,
    )

    second_candidate = await allocate_candidate(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
        student_id=second_student.id,
        candidate_number="CAND-002",
    )

    candidates = await list_assessment_candidates(
        db=db_session,
        current_user=teacher_user,
        assessment_id=assessment.id,
    )

    candidate_ids = {candidate.id for candidate in candidates}

    assert first_candidate.id in candidate_ids
    assert second_candidate.id in candidate_ids


@pytest.mark.asyncio
async def test_teacher_can_update_allocated_candidate_details(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.update.student@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    updated = await update_candidate_details(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
        candidate_number="NEW-001",
        access_arrangements="Laptop",
    )

    assert updated.candidate_number == "NEW-001"
    assert updated.access_arrangements == "Laptop"


# ----------------------------------------------------------------------
# Candidate lifecycle
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_candidate_cannot_start_before_assessment_is_published(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        assessment_status=AssessmentStatus.DRAFT,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.start.draft@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    with pytest.raises(HTTPException) as exc:
        await start_candidate(
            db=db_session,
            current_user=teacher_user,
            candidate_id=candidate.id,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_candidate_can_start_when_assessment_is_published(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        assessment_status=AssessmentStatus.PUBLISHED,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.start.published@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    started = await start_candidate(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    assert started.status == AssessmentCandidateStatus.STARTED
    assert started.started_at is not None


@pytest.mark.asyncio
async def test_started_candidate_can_be_submitted(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        assessment_status=AssessmentStatus.PUBLISHED,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.submit.student@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    await start_candidate(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    submitted = await submit_candidate(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    assert submitted.status == AssessmentCandidateStatus.SUBMITTED
    assert submitted.submitted_at is not None


@pytest.mark.asyncio
async def test_allocated_candidate_can_be_withdrawn(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.withdraw.student@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    withdrawn = await withdraw_candidate(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    assert withdrawn.status == AssessmentCandidateStatus.WITHDRAWN


@pytest.mark.asyncio
async def test_allocated_candidate_can_be_marked_absent(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.absent.student@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    absent = await mark_candidate_absent(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    assert absent.status == AssessmentCandidateStatus.ABSENT


@pytest.mark.asyncio
async def test_invalid_candidate_status_transition_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.invalid.transition@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    with pytest.raises(HTTPException) as exc:
        await transition_candidate_status(
            db=db_session,
            current_user=teacher_user,
            candidate_id=candidate.id,
            new_status=AssessmentCandidateStatus.SUBMITTED,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_invalid_candidate_status_value_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.invalid.status@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    with pytest.raises(HTTPException) as exc:
        await transition_candidate_status(
            db=db_session,
            current_user=teacher_user,
            candidate_id=candidate.id,
            new_status="not-a-real-status",
        )

    assert exc.value.status_code == 400


# ----------------------------------------------------------------------
# Candidate deletion
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_untouched_allocated_candidate_can_be_deleted(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.delete.student@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    candidate_id = candidate.id

    await delete_candidate(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate_id,
    )

    with pytest.raises(HTTPException) as exc:
        await get_candidate(
            db=db_session,
            current_user=teacher_user,
            candidate_id=candidate_id,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_started_candidate_cannot_be_deleted(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        assessment_status=AssessmentStatus.PUBLISHED,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="candidate.delete.started@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    await start_candidate(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    with pytest.raises(HTTPException) as exc:
        await delete_candidate(
            db=db_session,
            current_user=teacher_user,
            candidate_id=candidate.id,
        )

    assert exc.value.status_code == 409


# ----------------------------------------------------------------------
# Script creation and versioning
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_can_create_first_script_version(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="script.create.first@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    script = await create_script_version(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
        source_type="pdf_upload",
        source_filename="paper.pdf",
        storage_key="assessments/paper.pdf",
        mime_type="application/pdf",
        checksum="abc123",
    )

    assert script.id is not None
    assert script.candidate_id == candidate.id
    assert script.version == 1
    assert script.status == AssessmentScriptStatus.NOT_SUBMITTED
    assert script.source_type == "pdf_upload"
    assert script.source_filename == "paper.pdf"


@pytest.mark.asyncio
async def test_script_versions_increment(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="script.version.increment@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    first = await create_script_version(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    second = await create_script_version(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    assert first.version == 1
    assert second.version == 2


@pytest.mark.asyncio
async def test_withdrawn_candidate_cannot_receive_script(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="script.withdrawn.candidate@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    await withdraw_candidate(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    with pytest.raises(HTTPException) as exc:
        await create_script_version(
            db=db_session,
            current_user=teacher_user,
            candidate_id=candidate.id,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_teacher_can_get_script(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="script.get@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    script = await create_script_version(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    loaded = await get_script(
        db=db_session,
        current_user=teacher_user,
        script_id=script.id,
    )

    assert loaded.id == script.id
    assert loaded.candidate_id == candidate.id


@pytest.mark.asyncio
async def test_teacher_can_list_candidate_scripts(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="script.list@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    first = await create_script_version(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    second = await create_script_version(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    scripts = await list_candidate_scripts(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    assert [script.id for script in scripts] == [
        first.id,
        second.id,
    ]


# ----------------------------------------------------------------------
# Script lifecycle
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_script_can_be_submitted(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        assessment_status=AssessmentStatus.PUBLISHED,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="script.submit@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    script = await create_script_version(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    submitted = await submit_script(
        db=db_session,
        current_user=teacher_user,
        script_id=script.id,
    )

    assert submitted.status == AssessmentScriptStatus.SUBMITTED
    assert submitted.submitted_at is not None


@pytest.mark.asyncio
async def test_submitting_script_updates_candidate_to_submitted(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        assessment_status=AssessmentStatus.PUBLISHED,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="script.submit.candidate@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    script = await create_script_version(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    await submit_script(
        db=db_session,
        current_user=teacher_user,
        script_id=script.id,
    )

    loaded_candidate = await get_candidate(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    assert loaded_candidate.status == AssessmentCandidateStatus.SUBMITTED
    assert loaded_candidate.started_at is not None
    assert loaded_candidate.submitted_at is not None


@pytest.mark.asyncio
async def test_script_can_progress_through_marking_and_finalisation(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        assessment_status=AssessmentStatus.PUBLISHED,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="script.lifecycle@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    script = await create_script_version(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    await submit_script(
        db=db_session,
        current_user=teacher_user,
        script_id=script.id,
    )

    marking = await start_script_marking(
        db=db_session,
        current_user=teacher_user,
        script_id=script.id,
    )

    assert marking.status == AssessmentScriptStatus.MARKING
    assert marking.marking_started_at is not None

    marked = await mark_script_complete(
        db=db_session,
        current_user=teacher_user,
        script_id=script.id,
    )

    assert marked.status == AssessmentScriptStatus.MARKED
    assert marked.marked_at is not None

    moderated = await send_script_to_moderation(
        db=db_session,
        current_user=teacher_user,
        script_id=script.id,
    )

    assert moderated.status == AssessmentScriptStatus.MODERATION

    finalised = await finalise_script(
        db=db_session,
        current_user=teacher_user,
        script_id=script.id,
    )

    assert finalised.status == AssessmentScriptStatus.FINALISED
    assert finalised.finalised_at is not None


@pytest.mark.asyncio
async def test_marked_script_can_be_finalised_without_moderation(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        assessment_status=AssessmentStatus.PUBLISHED,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="script.direct.finalise@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    script = await create_script_version(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    await submit_script(
        db=db_session,
        current_user=teacher_user,
        script_id=script.id,
    )

    await start_script_marking(
        db=db_session,
        current_user=teacher_user,
        script_id=script.id,
    )

    await mark_script_complete(
        db=db_session,
        current_user=teacher_user,
        script_id=script.id,
    )

    finalised = await finalise_script(
        db=db_session,
        current_user=teacher_user,
        script_id=script.id,
    )

    assert finalised.status == AssessmentScriptStatus.FINALISED


@pytest.mark.asyncio
async def test_invalid_script_transition_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="script.invalid.transition@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    script = await create_script_version(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    with pytest.raises(HTTPException) as exc:
        await transition_script_status(
            db=db_session,
            current_user=teacher_user,
            script_id=script.id,
            new_status=AssessmentScriptStatus.MARKED,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_invalid_script_status_value_is_rejected(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="script.invalid.status@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    script = await create_script_version(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    with pytest.raises(HTTPException) as exc:
        await transition_script_status(
            db=db_session,
            current_user=teacher_user,
            script_id=script.id,
            new_status="not-a-real-status",
        )

    assert exc.value.status_code == 400


# ----------------------------------------------------------------------
# Script deletion
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unsubmitted_script_can_be_deleted(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="script.delete.unsubmitted@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    script = await create_script_version(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    script_id = script.id

    await delete_script(
        db=db_session,
        current_user=teacher_user,
        script_id=script_id,
    )

    with pytest.raises(HTTPException) as exc:
        await get_script(
            db=db_session,
            current_user=teacher_user,
            script_id=script_id,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_submitted_script_cannot_be_deleted(
    db_session: AsyncSession,
    teacher_user,
):
    _, assessment = await _create_assessment_for_teacher(
        db_session,
        teacher_user,
        assessment_status=AssessmentStatus.PUBLISHED,
    )

    student = await _create_student(
        db_session,
        school_id=teacher_user.school_id,
        email="script.delete.submitted@example.com",
    )

    candidate = await _allocate_test_candidate(
        db_session,
        teacher_user=teacher_user,
        assessment=assessment,
        student=student,
    )

    script = await create_script_version(
        db=db_session,
        current_user=teacher_user,
        candidate_id=candidate.id,
    )

    await submit_script(
        db=db_session,
        current_user=teacher_user,
        script_id=script.id,
    )

    with pytest.raises(HTTPException) as exc:
        await delete_script(
            db=db_session,
            current_user=teacher_user,
            script_id=script.id,
        )

    assert exc.value.status_code == 409
