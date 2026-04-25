import pytest
from fastapi import HTTPException

from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.user import UserRole
from app.services.assignment_submission_service import grade_submission, submit_assignment
from tests.conftest import create_test_user


@pytest.mark.asyncio
async def test_student_can_submit_published_assignment(db_session, student_user, teacher_user):
    assignment = Assignment(
        title="Test Assignment",
        description="Test",
        course_id=1,
        school_id=student_user.school_id,
        created_by=teacher_user.id,
        max_score=100,
        is_published=True,
    )
    db_session.add(assignment)
    await db_session.flush()

    submission = await submit_assignment(
        db=db_session,
        current_user=student_user,
        assignment_id=assignment.id,
        submission_text="My answer",
        attachment_url=None,
    )

    assert submission.id is not None
    assert submission.student_id == student_user.id
    assert submission.status == "submitted"


@pytest.mark.asyncio
async def test_student_cannot_submit_unpublished_assignment(db_session, student_user, teacher_user):
    assignment = Assignment(
        title="Draft Assignment",
        description="Draft",
        course_id=1,
        school_id=student_user.school_id,
        created_by=teacher_user.id,
        max_score=100,
        is_published=False,
    )
    db_session.add(assignment)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc:
        await submit_assignment(
            db=db_session,
            current_user=student_user,
            assignment_id=assignment.id,
            submission_text="My answer",
            attachment_url=None,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_teacher_can_grade_own_assignment_submission(db_session, student_user, teacher_user):
    assignment = Assignment(
        title="Gradable Assignment",
        description="Test",
        course_id=1,
        school_id=teacher_user.school_id,
        created_by=teacher_user.id,
        max_score=100,
        is_published=True,
    )
    db_session.add(assignment)
    await db_session.flush()

    submission = AssignmentSubmission(
        assignment_id=assignment.id,
        student_id=student_user.id,
        school_id=student_user.school_id,
        submission_text="Answer",
        status="submitted",
    )
    db_session.add(submission)
    await db_session.flush()

    graded = await grade_submission(
        db=db_session,
        submission_id=submission.id,
        current_user=teacher_user,
        score=85,
        feedback="Good work",
    )

    assert graded.status == "graded"
    assert graded.score == 85
    assert graded.feedback == "Good work"
    assert graded.graded_by == teacher_user.id


@pytest.mark.asyncio
async def test_teacher_cannot_grade_other_teachers_assignment(db_session, student_user, teacher_user):
    other_teacher = await create_test_user(
        db_session,
        email="other.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=teacher_user.school_id,
    )

    assignment = Assignment(
        title="Other Teacher Assignment",
        description="Test",
        course_id=1,
        school_id=teacher_user.school_id,
        created_by=other_teacher.id,
        max_score=100,
        is_published=True,
    )
    db_session.add(assignment)
    await db_session.flush()

    submission = AssignmentSubmission(
        assignment_id=assignment.id,
        student_id=student_user.id,
        school_id=student_user.school_id,
        submission_text="Answer",
        status="submitted",
    )
    db_session.add(submission)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc:
        await grade_submission(
            db=db_session,
            submission_id=submission.id,
            current_user=teacher_user,
            score=70,
            feedback="No",
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_school_admin_teacher_can_grade_any_school_assignment(
    db_session,
    student_user,
    teacher_user,
    school_admin_teacher_user,
):
    assignment = Assignment(
        title="Admin Grading Assignment",
        description="Test",
        course_id=1,
        school_id=school_admin_teacher_user.school_id,
        created_by=teacher_user.id,
        max_score=100,
        is_published=True,
    )
    db_session.add(assignment)
    await db_session.flush()

    submission = AssignmentSubmission(
        assignment_id=assignment.id,
        student_id=student_user.id,
        school_id=student_user.school_id,
        submission_text="Answer",
        status="submitted",
    )
    db_session.add(submission)
    await db_session.flush()

    graded = await grade_submission(
        db=db_session,
        submission_id=submission.id,
        current_user=school_admin_teacher_user,
        score=90,
        feedback="Excellent",
    )

    assert graded.status == "graded"
    assert graded.score == 90
    assert graded.graded_by == school_admin_teacher_user.id
