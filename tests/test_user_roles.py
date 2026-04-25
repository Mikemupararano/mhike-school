import pytest

from app.models.user import UserRole


@pytest.mark.asyncio
async def test_user_multiple_roles(db_session, school_admin_teacher_user):
    user = school_admin_teacher_user

    assert UserRole.SCHOOL_ADMIN.value in user.roles
    assert UserRole.TEACHER.value in user.roles


@pytest.mark.asyncio
async def test_user_role_flags(db_session, school_admin_teacher_user):
    user = school_admin_teacher_user

    assert user.is_school_admin is True
    assert user.is_teacher is True
    assert user.is_student is False


@pytest.mark.asyncio
async def test_user_can_teach(db_session, school_admin_teacher_user):
    user = school_admin_teacher_user

    assert user.can_teach is True


@pytest.mark.asyncio
async def test_student_cannot_teach(db_session, student_user):
    user = student_user

    assert user.can_teach is False
