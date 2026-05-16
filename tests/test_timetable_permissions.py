import pytest
from fastapi import HTTPException

from app.core.permissions import PermissionService


@pytest.mark.asyncio
async def test_teacher_can_access_timetable_features(
    teacher_user,
):
    PermissionService.ensure_school_admin_or_teacher(teacher_user)


@pytest.mark.asyncio
async def test_school_admin_can_access_timetable_features(
    school_admin_teacher_user,
):
    PermissionService.ensure_school_admin_or_teacher(school_admin_teacher_user)


@pytest.mark.asyncio
async def test_student_cannot_manage_timetables(
    student_user,
):
    with pytest.raises(HTTPException) as exc:
        PermissionService.ensure_school_admin_or_teacher(student_user)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_teacher_can_view_own_timetable(
    teacher_user,
):
    PermissionService.ensure_can_teach(teacher_user)


@pytest.mark.asyncio
async def test_student_cannot_access_teacher_permissions(
    student_user,
):
    with pytest.raises(HTTPException) as exc:
        PermissionService.ensure_can_teach(student_user)

    assert exc.value.status_code == 403
