import pytest

pytestmark = pytest.mark.asyncio


async def test_teacher_cannot_access_student_attendance_profile(
    client,
    teacher_user,
    student_user,
    auth_headers,
):
    response = await client.get(
        f"/api/v1/student-attendance/students/{student_user.id}/profile",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 403


async def test_student_cannot_access_student_attendance_profile(
    client,
    student_user,
    auth_headers,
):
    response = await client.get(
        f"/api/v1/student-attendance/students/{student_user.id}/profile",
        headers=auth_headers(student_user),
    )

    assert response.status_code == 403


async def test_parent_cannot_access_student_attendance_profile(
    client,
    parent_user,
    student_user,
    auth_headers,
):
    response = await client.get(
        f"/api/v1/student-attendance/students/{student_user.id}/profile",
        headers=auth_headers(parent_user),
    )

    assert response.status_code == 403


async def test_school_admin_can_access_student_attendance_profile(
    client,
    school_admin_user,
    student_user,
    auth_headers,
):
    response = await client.get(
        f"/api/v1/student-attendance/students/{student_user.id}/profile",
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200


async def test_platform_admin_without_school_context_gets_error(
    client,
    platform_admin_user,
    student_user,
    auth_headers,
):
    response = await client.get(
        f"/api/v1/student-attendance/students/{student_user.id}/profile",
        headers=auth_headers(platform_admin_user),
    )

    assert response.status_code in (400, 403)
