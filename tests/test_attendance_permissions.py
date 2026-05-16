from datetime import date

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.core.permissions import PermissionService


@pytest.mark.asyncio
async def test_teacher_can_access_attendance_permissions(teacher_user):
    PermissionService.ensure_can_teach(teacher_user)


@pytest.mark.asyncio
async def test_school_admin_can_access_attendance_permissions(school_admin_user):
    PermissionService.ensure_school_admin_or_platform_admin(school_admin_user)


@pytest.mark.asyncio
async def test_student_cannot_access_attendance_permissions(student_user):
    with pytest.raises(HTTPException) as exc:
        PermissionService.ensure_can_teach(student_user)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_teacher_can_create_attendance_session(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.post(
        "/api/v1/attendance/sessions",
        headers=auth_headers(teacher_user),
        json={
            "school_id": 1,
            "class_group_id": 1,
            "session_date": str(date.today()),
            "session_type": "am",
        },
    )

    assert response.status_code in (200, 201)


@pytest.mark.asyncio
async def test_student_cannot_create_attendance_session(
    client: AsyncClient,
    student_user,
    auth_headers,
):
    response = await client.post(
        "/api/v1/attendance/sessions",
        headers=auth_headers(student_user),
        json={
            "school_id": 1,
            "class_group_id": 1,
            "session_date": str(date.today()),
            "session_type": "am",
        },
    )

    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_school_admin_can_view_attendance_sessions(
    client: AsyncClient,
    school_admin_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/attendance/sessions",
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_platform_admin_can_view_attendance_sessions(
    client: AsyncClient,
    platform_admin_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/attendance/sessions",
        headers=auth_headers(platform_admin_user),
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_access_attendance(
    client: AsyncClient,
):
    response = await client.get("/api/v1/attendance/sessions")

    assert response.status_code in (401, 403)
