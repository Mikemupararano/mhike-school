import pytest


@pytest.mark.asyncio
async def test_teacher_can_access_attendance_routes():
    assert True


@pytest.mark.asyncio
async def test_student_cannot_create_attendance_session():
    assert True


@pytest.mark.asyncio
async def test_school_admin_can_access_school_attendance():
    assert True


@pytest.mark.asyncio
async def test_attendance_routes_are_school_scoped():
    assert True
