import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.parent_student import ParentStudent


@pytest.mark.asyncio
async def test_linked_parent_can_view_child_grades(
    client: AsyncClient,
    db_session: AsyncSession,
    parent_user,
    student_user,
    school_admin_user,
    auth_headers,
):
    link = ParentStudent(
        parent_id=parent_user.id,
        student_id=student_user.id,
    )

    assignment = Assignment(
        title="Rates of Reaction Homework",
        description="Complete the rates questions.",
        course_id=1,
        school_id=school_admin_user.school_id,
        created_by=school_admin_user.id,
        max_score=20,
        is_published=True,
    )

    db_session.add_all([link, assignment])
    await db_session.flush()

    submission = AssignmentSubmission(
        assignment_id=assignment.id,
        student_id=student_user.id,
        school_id=school_admin_user.school_id,
        submission_text="Completed work",
        status="graded",
        score=18,
        feedback="Excellent application of collision theory.",
        graded_by=school_admin_user.id,
    )

    db_session.add(submission)
    await db_session.commit()

    response = await client.get(
        "/api/v1/assignment-submissions/parent/grades",
        headers=auth_headers(parent_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["assignment_title"] == "Rates of Reaction Homework"
    assert data[0]["student_id"] == student_user.id
    assert data[0]["score"] == 18
    assert data[0]["max_score"] == 20
    assert data[0]["feedback"] == "Excellent application of collision theory."


@pytest.mark.asyncio
async def test_unlinked_parent_cannot_view_child_grades(
    client: AsyncClient,
    db_session: AsyncSession,
    parent_user,
    student_user,
    school_admin_user,
    auth_headers,
):
    assignment = Assignment(
        title="Unlinked Student Homework",
        description="Private assignment.",
        course_id=1,
        school_id=school_admin_user.school_id,
        created_by=school_admin_user.id,
        max_score=10,
        is_published=True,
    )

    db_session.add(assignment)
    await db_session.flush()

    submission = AssignmentSubmission(
        assignment_id=assignment.id,
        student_id=student_user.id,
        school_id=school_admin_user.school_id,
        submission_text="Private work",
        status="graded",
        score=7,
        feedback="Private feedback.",
        graded_by=school_admin_user.id,
    )

    db_session.add(submission)
    await db_session.commit()

    response = await client.get(
        "/api/v1/assignment-submissions/parent/grades",
        headers=auth_headers(parent_user),
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_student_cannot_view_parent_grades_endpoint(
    client: AsyncClient,
    student_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/assignment-submissions/parent/grades",
        headers=auth_headers(student_user),
    )

    assert response.status_code == 403
