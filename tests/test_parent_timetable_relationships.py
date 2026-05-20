import pytest

pytestmark = pytest.mark.asyncio


async def test_parent_can_access_linked_child_timetable(
    client,
    parent_user,
    student_user,
    auth_headers,
):
    response = await client.get(
        f"/api/v1/timetables/parent/child/{student_user.id}",
        headers=auth_headers(parent_user),
    )

    assert response.status_code in (200, 404)


async def test_student_cannot_access_parent_child_timetable_endpoint(
    client,
    student_user,
    auth_headers,
):
    response = await client.get(
        f"/api/v1/timetables/parent/child/{student_user.id}",
        headers=auth_headers(student_user),
    )

    assert response.status_code == 403


async def test_teacher_cannot_access_parent_child_timetable_endpoint(
    client,
    teacher_user,
    student_user,
    auth_headers,
):
    response = await client.get(
        f"/api/v1/timetables/parent/child/{student_user.id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 403
