from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.imports.processors.attendance import process_attendance_row
from app.imports.validators.attendance import validate_attendance_row
from app.models.class_group import ClassGroup
from app.models.user import User


async def create_class_group(
    db_session: AsyncSession,
    *,
    school_id: int,
    teacher_user: User,
    name: str = "10A",
) -> ClassGroup:
    """
    Create a class group required by attendance processor tests.
    """

    class_group = ClassGroup(
        name=name,
        school_id=school_id,
        teacher_id=teacher_user.id,
    )

    db_session.add(
        class_group,
    )
    await db_session.commit()
    await db_session.refresh(
        class_group,
    )

    return class_group


def test_validate_attendance_row_success() -> None:
    result = validate_attendance_row(
        {
            "class_name": "10A",
            "session_date": "2026-09-01",
            "session_type": "am",
            "student_email": "student@example.com",
            "status": "present",
            "marked_by_email": "teacher@example.com",
            "notes": "Arrived on time.",
        },
    )

    assert result.is_valid is True
    assert result.errors == []
    assert result.normalised_data is not None

    assert result.normalised_data["class_name"] == "10A"
    assert result.normalised_data["session_date"] == "2026-09-01"
    assert result.normalised_data["session_type"] == "am"
    assert result.normalised_data["student_email"] == ("student@example.com")
    assert result.normalised_data["status"] == "present"
    assert result.normalised_data["marked_by_email"] == ("teacher@example.com")
    assert result.normalised_data["notes"] == "Arrived on time."


def test_validate_attendance_requires_class() -> None:
    result = validate_attendance_row(
        {
            "session_date": "2026-09-01",
            "session_type": "am",
            "student_email": "student@example.com",
            "status": "present",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_attendance_requires_session_date() -> None:
    result = validate_attendance_row(
        {
            "class_name": "10A",
            "session_type": "am",
            "student_email": "student@example.com",
            "status": "present",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_attendance_requires_session_type() -> None:
    result = validate_attendance_row(
        {
            "class_name": "10A",
            "session_date": "2026-09-01",
            "student_email": "student@example.com",
            "status": "present",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_attendance_requires_student() -> None:
    result = validate_attendance_row(
        {
            "class_name": "10A",
            "session_date": "2026-09-01",
            "session_type": "am",
            "status": "present",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_attendance_requires_status() -> None:
    result = validate_attendance_row(
        {
            "class_name": "10A",
            "session_date": "2026-09-01",
            "session_type": "am",
            "student_email": "student@example.com",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_attendance_rejects_invalid_date() -> None:
    result = validate_attendance_row(
        {
            "class_name": "10A",
            "session_date": "1 September 2026",
            "session_type": "am",
            "student_email": "student@example.com",
            "status": "present",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_attendance_rejects_invalid_session_type() -> None:
    result = validate_attendance_row(
        {
            "class_name": "10A",
            "session_date": "2026-09-01",
            "session_type": "evening",
            "student_email": "student@example.com",
            "status": "present",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_attendance_rejects_invalid_status() -> None:
    result = validate_attendance_row(
        {
            "class_name": "10A",
            "session_date": "2026-09-01",
            "session_type": "am",
            "student_email": "student@example.com",
            "status": "missing",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_attendance_rejects_invalid_student_email() -> None:
    result = validate_attendance_row(
        {
            "class_name": "10A",
            "session_date": "2026-09-01",
            "session_type": "am",
            "student_email": "not-an-email",
            "status": "present",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_attendance_rejects_invalid_marker_email() -> None:
    result = validate_attendance_row(
        {
            "class_name": "10A",
            "session_date": "2026-09-01",
            "session_type": "am",
            "student_email": "student@example.com",
            "status": "present",
            "marked_by_email": "not-an-email",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None


def test_validate_attendance_defaults() -> None:
    result = validate_attendance_row(
        {
            "class_name": "10A",
            "session_date": "2026-09-01",
            "session_type": "pm",
            "student_email": "student@example.com",
            "status": "late",
        },
    )

    assert result.is_valid is True
    assert result.normalised_data is not None
    assert result.normalised_data["marked_by_email"] is None
    assert result.normalised_data["notes"] is None


@pytest.mark.asyncio
async def test_process_attendance_invalid_school(
    db_session: AsyncSession,
) -> None:
    with pytest.raises(
        ValueError,
        match="school_id must be a positive integer",
    ):
        await process_attendance_row(
            db_session,
            {
                "class_name": "10A",
                "session_date": "2026-09-01",
                "session_type": "am",
                "student_email": "student@example.com",
                "status": "present",
            },
            0,
        )


@pytest.mark.asyncio
async def test_process_attendance_missing_class(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    with pytest.raises(
        ValueError,
        match="No class named",
    ):
        await process_attendance_row(
            db_session,
            {
                "class_name": "Missing Class",
                "session_date": "2026-09-01",
                "session_type": "am",
                "student_email": "student@example.com",
                "status": "present",
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_process_attendance_missing_student(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    class_group = await create_class_group(
        db_session,
        school_id=school_id,
        teacher_user=teacher_user,
    )

    with pytest.raises(
        ValueError,
        match="No student with email",
    ):
        await process_attendance_row(
            db_session,
            {
                "class_name": class_group.name,
                "session_date": "2026-09-01",
                "session_type": "am",
                "student_email": "missing@example.com",
                "status": "present",
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_process_attendance_invalid_marker(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id
    assert student_user.school_id == school_id

    class_group = await create_class_group(
        db_session,
        school_id=school_id,
        teacher_user=teacher_user,
    )

    with pytest.raises(
        ValueError,
        match="No attendance marker",
    ):
        await process_attendance_row(
            db_session,
            {
                "class_name": class_group.name,
                "session_date": "2026-09-01",
                "session_type": "am",
                "student_email": student_user.email,
                "status": "present",
                "marked_by_email": "missing@example.com",
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_process_attendance_marker_not_authorised(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id
    assert student_user.school_id == school_id

    class_group = await create_class_group(
        db_session,
        school_id=school_id,
        teacher_user=teacher_user,
    )

    with pytest.raises(
        ValueError,
        match="not authorised to mark attendance",
    ):
        await process_attendance_row(
            db_session,
            {
                "class_name": class_group.name,
                "session_date": "2026-09-01",
                "session_type": "am",
                "student_email": student_user.email,
                "status": "present",
                "marked_by_email": student_user.email,
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_process_attendance_missing_session(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id
    assert student_user.school_id == school_id

    class_group = await create_class_group(
        db_session,
        school_id=school_id,
        teacher_user=teacher_user,
    )

    with pytest.raises(
        ValueError,
        match="attendance session",
    ):
        await process_attendance_row(
            db_session,
            {
                "class_name": class_group.name,
                "session_date": "2035-01-01",
                "session_type": "am",
                "student_email": student_user.email,
                "status": "present",
                "marked_by_email": teacher_user.email,
            },
            school_id,
        )
