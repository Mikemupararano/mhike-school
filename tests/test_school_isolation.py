import pytest
from fastapi import HTTPException

from app.core.permissions import PermissionService


@pytest.mark.asyncio
async def test_school_admin_can_access_same_school(school_admin_user):
    PermissionService.ensure_same_school(
        school_admin_user,
        school_admin_user.school_id,
    )


@pytest.mark.asyncio
async def test_school_admin_cannot_access_other_school(school_admin_user):
    with pytest.raises(HTTPException) as exc:
        PermissionService.ensure_same_school(school_admin_user, 999)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_platform_admin_can_access_any_school(platform_admin_user):
    PermissionService.ensure_same_school(platform_admin_user, 999)
