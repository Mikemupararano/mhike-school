from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.user import UserRole
from tests.conftest import create_test_user


@pytest.mark.asyncio
async def test_school_admin_can_create_course_for_teacher(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    auth_headers,
):
    teacher = await create_test_user(
        db_session,
        email="school.admin.course.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=school_admin_user.school_id,
    )

    response = await client.post(
        "/api/v1/school-admin/courses",
        json={
            "title": "Physics",
            "description": "A Level Physics",
            "teacher_id": teacher.id,
            "published": True,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["id"] is not None
    assert data["title"] == "Physics"
    assert data["description"] == "A Level Physics"
    assert data["teacher_id"] == teacher.id
    assert data["teacher_name"] == teacher.full_name
    assert data["school_id"] == school_admin_user.school_id
    assert data["published"] is True


@pytest.mark.asyncio
async def test_school_admin_created_course_is_persisted(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    auth_headers,
):
    teacher = await create_test_user(
        db_session,
        email="school.admin.course.persist@example.com",
        roles=[UserRole.TEACHER],
        school_id=school_admin_user.school_id,
    )

    response = await client.post(
        "/api/v1/school-admin/courses",
        json={
            "title": "Chemistry",
            "teacher_id": teacher.id,
            "published": False,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 201, response.text

    course_id = response.json()["id"]

    course = await db_session.get(
        Course,
        course_id,
    )

    assert course is not None
    assert course.title == "Chemistry"
    assert course.teacher_id == teacher.id
    assert course.school_id == school_admin_user.school_id
    assert course.published is False


@pytest.mark.asyncio
async def test_school_admin_can_reassign_course_to_another_teacher(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    auth_headers,
):
    first_teacher = await create_test_user(
        db_session,
        email="school.admin.course.first@example.com",
        roles=[UserRole.TEACHER],
        school_id=school_admin_user.school_id,
    )

    second_teacher = await create_test_user(
        db_session,
        email="school.admin.course.second@example.com",
        roles=[UserRole.TEACHER],
        school_id=school_admin_user.school_id,
    )

    create_response = await client.post(
        "/api/v1/school-admin/courses",
        json={
            "title": "Biology",
            "teacher_id": first_teacher.id,
            "published": True,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert create_response.status_code == 201, create_response.text

    course_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/school-admin/courses/{course_id}",
        json={
            "teacher_id": second_teacher.id,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["teacher_id"] == second_teacher.id
    assert data["teacher_name"] == second_teacher.full_name


@pytest.mark.asyncio
async def test_school_admin_can_update_course_metadata(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    auth_headers,
):
    teacher = await create_test_user(
        db_session,
        email="school.admin.course.metadata@example.com",
        roles=[UserRole.TEACHER],
        school_id=school_admin_user.school_id,
    )

    create_response = await client.post(
        "/api/v1/school-admin/courses",
        json={
            "title": "Old Course Title",
            "description": "Old description",
            "teacher_id": teacher.id,
            "published": False,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert create_response.status_code == 201, create_response.text

    course_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/school-admin/courses/{course_id}",
        json={
            "title": "Updated Course Title",
            "description": "Updated description",
            "published": True,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["title"] == "Updated Course Title"
    assert data["description"] == "Updated description"
    assert data["published"] is True


@pytest.mark.asyncio
async def test_school_admin_course_creation_rejects_non_teacher(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    auth_headers,
):
    student = await create_test_user(
        db_session,
        email="school.admin.course.student@example.com",
        roles=[UserRole.STUDENT],
        school_id=school_admin_user.school_id,
    )

    response = await client.post(
        "/api/v1/school-admin/courses",
        json={
            "title": "Invalid Course",
            "teacher_id": student.id,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_school_admin_course_creation_rejects_teacher_from_another_school(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    auth_headers,
):
    other_teacher = await create_test_user(
        db_session,
        email="school.admin.course.other.school@example.com",
        roles=[UserRole.TEACHER],
        school_id=school_admin_user.school_id + 999,
    )

    response = await client.post(
        "/api/v1/school-admin/courses",
        json={
            "title": "Cross School Course",
            "teacher_id": other_teacher.id,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_school_admin_course_update_rejects_course_from_another_school(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    auth_headers,
):
    other_teacher = await create_test_user(
        db_session,
        email="school.admin.course.foreign.owner@example.com",
        roles=[UserRole.TEACHER],
        school_id=school_admin_user.school_id + 999,
    )

    foreign_course = Course(
        title="Foreign Course",
        description="Another school's course.",
        teacher_id=other_teacher.id,
        school_id=other_teacher.school_id,
        published=True,
    )

    db_session.add(
        foreign_course,
    )

    await db_session.commit()
    await db_session.refresh(
        foreign_course,
    )

    response = await client.patch(
        f"/api/v1/school-admin/courses/{foreign_course.id}",
        json={
            "title": "Should Not Change",
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_teacher_cannot_use_school_admin_course_creation_endpoint(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    response = await client.post(
        "/api/v1/school-admin/courses",
        json={
            "title": "Forbidden Course",
            "teacher_id": teacher_user.id,
        },
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert response.status_code == 403
