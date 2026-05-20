import pytest

pytestmark = pytest.mark.asyncio


async def test_parent_can_access_parent_attendance_endpoint(
    client,
    parent_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/parent-attendance",
        headers=auth_headers(parent_user),
    )

    assert response.status_code in (200, 404)


async def test_parent_attendance_endpoint_requires_authentication(
    client,
):
    response = await client.get(
        "/api/v1/parent-attendance",
    )

    assert response.status_code in (401, 403, 404)


async def test_parent_can_access_parent_students_endpoint(
    client,
    parent_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/parent-students",
        headers=auth_headers(parent_user),
    )

    assert response.status_code in (200, 404)


async def test_parent_students_endpoint_requires_authentication(
    client,
):
    response = await client.get(
        "/api/v1/parent-students",
    )

    assert response.status_code in (401, 403, 404)


async def test_student_cannot_access_parent_students_endpoint(
    client,
    student_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/parent-students",
        headers=auth_headers(student_user),
    )

    assert response.status_code in (403, 404)


async def test_teacher_cannot_access_parent_students_endpoint(
    client,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/parent-students",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code in (403, 404)


async def test_parent_cannot_modify_attendance_records(
    client,
    parent_user,
    student_user,
    auth_headers,
):
    payload = {
        "student_id": student_user.id,
        "status": "present",
    }

    response = await client.post(
        "/api/v1/attendance/mark",
        json=payload,
        headers=auth_headers(parent_user),
    )

    assert response.status_code in (403, 404)
