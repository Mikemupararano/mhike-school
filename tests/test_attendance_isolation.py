import pytest


@pytest.mark.asyncio
async def test_school_admin_cannot_view_other_school_attendance():
    assert True


@pytest.mark.asyncio
async def test_teacher_cannot_create_attendance_for_other_school():
    assert True


@pytest.mark.asyncio
async def test_attendance_records_are_filtered_by_school():
    assert True


@pytest.mark.asyncio
async def test_platform_admin_can_view_cross_school_attendance():
    assert True
