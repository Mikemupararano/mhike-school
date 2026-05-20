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


async def test_teacher_cannot_modify_attendance_without_valid_attendance_route(
    client,
    teacher_user,
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
        headers=auth_headers(teacher_user),
    )

    assert response.status_code in (403, 404, 422)


async def test_teacher_cannot_bulk_update_attendance_without_valid_payload(
    client,
    teacher_user,
    student_user,
    auth_headers,
):
    payload = {
        "records": [
            {
                "student_id": student_user.id,
                "status": "present",
            }
        ]
    }

    response = await client.post(
        "/api/v1/attendance/bulk",
        json=payload,
        headers=auth_headers(teacher_user),
    )

    assert response.status_code in (403, 404, 422)


async def test_teacher_cannot_access_admin_attendance_dashboard_without_scope(
    client,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/attendance-dashboard/summary",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code in (403, 404, 422)


async def test_teacher_cannot_access_attendance_analytics_without_scope(
    client,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/attendance-analytics/summary",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code in (403, 404, 422)
