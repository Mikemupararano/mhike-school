import pytest
from fastapi import HTTPException

from app.core.permissions import PermissionService
from app.models.user import UserRole


@pytest.mark.asyncio
async def test_school_admin_teacher_passes_school_admin_permission(
    school_admin_teacher_user,
):
    PermissionService.ensure_school_admin_or_platform_admin(
        school_admin_teacher_user
    )


@pytest.mark.asyncio
async def test_teacher_fails_school_admin_permission(teacher_user):
    with pytest.raises(HTTPException) as exc:
        PermissionService.ensure_school_admin_or_platform_admin(teacher_user)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_school_admin_teacher_can_teach(school_admin_teacher_user):
    PermissionService.ensure_can_teach(school_admin_teacher_user)


@pytest.mark.asyncio
async def test_student_cannot_teach(student_user):
    with pytest.raises(HTTPException) as exc:
        PermissionService.ensure_can_teach(student_user)

    assert exc.value.status_code == 403
