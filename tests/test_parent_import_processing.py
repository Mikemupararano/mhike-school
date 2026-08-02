from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.imports.processors.parents import process_parent_row
from app.imports.registry import RowProcessingAction
from app.imports.validators.parents import validate_parent_row
from app.models.parent_student import ParentStudent
from app.models.user import User, UserRole
from app.repositories.parent_student import ParentStudentRepository
from app.repositories.user import UserRepository


def test_validate_parent_row_success() -> None:
    result = validate_parent_row(
        {
            "email": " parent@example.com ",
            "first_name": " John ",
            "last_name": " Smith ",
            "student_email": " student@example.com ",
            "phone": " 01234567890 ",
            "relationship": "Father",
        },
    )

    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == []

    assert result.normalised_data is not None
    assert result.normalised_data["email"] == "parent@example.com"
    assert result.normalised_data["first_name"] == "John"
    assert result.normalised_data["last_name"] == "Smith"
    assert result.normalised_data["student_email"] == ("student@example.com")
    assert result.normalised_data["phone"] == "01234567890"

    # Extra fields remain available for future parent-import expansion.
    assert result.normalised_data["relationship"] == "Father"


def test_validate_parent_row_requires_parent_email() -> None:
    result = validate_parent_row(
        {
            "first_name": "John",
            "last_name": "Smith",
            "student_email": "student@example.com",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None

    error_locations = {tuple(error["loc"]) for error in result.errors}

    assert ("email",) in error_locations


def test_validate_parent_row_requires_student_email() -> None:
    result = validate_parent_row(
        {
            "email": "parent@example.com",
            "first_name": "John",
            "last_name": "Smith",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None

    error_locations = {tuple(error["loc"]) for error in result.errors}

    assert ("student_email",) in error_locations


def test_validate_parent_row_requires_first_name() -> None:
    result = validate_parent_row(
        {
            "email": "parent@example.com",
            "last_name": "Smith",
            "student_email": "student@example.com",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None

    error_locations = {tuple(error["loc"]) for error in result.errors}

    assert ("first_name",) in error_locations


def test_validate_parent_row_requires_last_name() -> None:
    result = validate_parent_row(
        {
            "email": "parent@example.com",
            "first_name": "John",
            "student_email": "student@example.com",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None

    error_locations = {tuple(error["loc"]) for error in result.errors}

    assert ("last_name",) in error_locations


def test_validate_parent_row_rejects_invalid_email_addresses() -> None:
    result = validate_parent_row(
        {
            "email": "not-an-email",
            "first_name": "John",
            "last_name": "Smith",
            "student_email": "also-not-an-email",
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None

    error_locations = {tuple(error["loc"]) for error in result.errors}

    assert ("email",) in error_locations
    assert ("student_email",) in error_locations


def test_validate_parent_row_rejects_long_phone() -> None:
    result = validate_parent_row(
        {
            "email": "parent@example.com",
            "first_name": "John",
            "last_name": "Smith",
            "student_email": "student@example.com",
            "phone": "1" * 51,
        },
    )

    assert result.is_valid is False
    assert result.normalised_data is None

    error_locations = {tuple(error["loc"]) for error in result.errors}

    assert ("phone",) in error_locations


@pytest.mark.asyncio
async def test_process_parent_row_creates_parent_and_link(
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert student_user.school_id == school_id

    result = await process_parent_row(
        db_session,
        {
            "email": " new.parent@example.com ",
            "first_name": " New ",
            "last_name": " Parent ",
            "student_email": student_user.email.upper(),
        },
        school_id,
    )

    await db_session.commit()

    parent = await UserRepository(
        db_session,
    ).get_by_email(
        email="new.parent@example.com",
        school_id=school_id,
    )

    assert parent is not None
    assert parent.full_name == "New Parent"
    assert parent.has_role(UserRole.PARENT)
    assert parent.is_active is True

    link = await ParentStudentRepository(
        db_session,
    ).get_link_in_school(
        parent_id=parent.id,
        student_id=student_user.id,
        school_id=school_id,
    )

    assert link is not None
    assert result.action == RowProcessingAction.CREATED
    assert result.entity_id == link.id
    assert result.message is not None
    assert "Created parent" in result.message


@pytest.mark.asyncio
async def test_process_parent_row_updates_existing_parent_and_creates_link(
    db_session: AsyncSession,
    school_admin_user: User,
    parent_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert parent_user.school_id == school_id
    assert student_user.school_id == school_id

    result = await process_parent_row(
        db_session,
        {
            "email": parent_user.email.upper(),
            "first_name": "Updated",
            "last_name": "Parent",
            "student_email": student_user.email,
        },
        school_id,
    )

    await db_session.commit()
    await db_session.refresh(parent_user)

    link = await ParentStudentRepository(
        db_session,
    ).get_link_in_school(
        parent_id=parent_user.id,
        student_id=student_user.id,
        school_id=school_id,
    )

    assert result.action == RowProcessingAction.UPDATED
    assert result.entity_id is not None
    assert result.message is not None
    assert "Updated parent" in result.message

    assert parent_user.full_name == "Updated Parent"
    assert parent_user.has_role(UserRole.PARENT)
    assert parent_user.is_active is True

    assert link is not None
    assert link.id == result.entity_id


@pytest.mark.asyncio
async def test_process_parent_row_duplicate_link_is_skipped(
    db_session: AsyncSession,
    school_admin_user: User,
    parent_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert parent_user.school_id == school_id
    assert student_user.school_id == school_id

    existing_link = ParentStudent(
        parent_id=parent_user.id,
        student_id=student_user.id,
    )

    db_session.add(existing_link)
    await db_session.commit()
    await db_session.refresh(existing_link)

    result = await process_parent_row(
        db_session,
        {
            "email": parent_user.email,
            "first_name": "Updated",
            "last_name": "Parent",
            "student_email": student_user.email,
        },
        school_id,
    )

    await db_session.commit()

    matching_links = (
        (
            await db_session.execute(
                select(ParentStudent).where(
                    ParentStudent.parent_id == parent_user.id,
                    ParentStudent.student_id == student_user.id,
                ),
            )
        )
        .scalars()
        .all()
    )

    assert result.action == RowProcessingAction.SKIPPED
    assert result.entity_id == existing_link.id
    assert result.message is not None
    assert "already linked" in result.message

    assert len(matching_links) == 1
    assert matching_links[0].id == existing_link.id


@pytest.mark.asyncio
async def test_process_parent_row_missing_student_raises(
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    with pytest.raises(
        ValueError,
        match="No student with email",
    ):
        await process_parent_row(
            db_session,
            {
                "email": "parent@example.com",
                "first_name": "John",
                "last_name": "Smith",
                "student_email": "missing@example.com",
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_process_parent_row_rejects_non_student_link_target(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id

    with pytest.raises(
        ValueError,
        match="is not registered as a student",
    ):
        await process_parent_row(
            db_session,
            {
                "email": "parent@example.com",
                "first_name": "John",
                "last_name": "Smith",
                "student_email": teacher_user.email,
            },
            school_id,
        )


@pytest.mark.asyncio
async def test_process_parent_row_rejects_existing_non_parent_user(
    db_session: AsyncSession,
    school_admin_user: User,
    teacher_user: User,
    student_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None
    assert teacher_user.school_id == school_id
    assert student_user.school_id == school_id

    with pytest.raises(
        ValueError,
        match="A non-parent user with email",
    ):
        await process_parent_row(
            db_session,
            {
                "email": teacher_user.email,
                "first_name": "Incorrect",
                "last_name": "Conversion",
                "student_email": student_user.email,
            },
            school_id,
        )


@pytest.mark.parametrize(
    "school_id",
    [
        0,
        -1,
        -999,
    ],
)
@pytest.mark.asyncio
async def test_process_parent_row_rejects_invalid_school_id(
    db_session: AsyncSession,
    school_id: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="school_id must be a positive integer",
    ):
        await process_parent_row(
            db_session,
            {
                "email": "parent@example.com",
                "first_name": "John",
                "last_name": "Smith",
                "student_email": "student@example.com",
            },
            school_id,
        )


@pytest.mark.parametrize(
    (
        "row",
        "expected_message",
    ),
    [
        (
            {
                "first_name": "John",
                "last_name": "Smith",
                "student_email": "student@example.com",
            },
            "Parent import field 'email' is required.",
        ),
        (
            {
                "email": "   ",
                "first_name": "John",
                "last_name": "Smith",
                "student_email": "student@example.com",
            },
            "Parent import field 'email' cannot be blank.",
        ),
        (
            {
                "email": "parent@example.com",
                "last_name": "Smith",
                "student_email": "student@example.com",
            },
            "Parent import field 'first_name' is required.",
        ),
        (
            {
                "email": "parent@example.com",
                "first_name": "John",
                "student_email": "student@example.com",
            },
            "Parent import field 'last_name' is required.",
        ),
        (
            {
                "email": "parent@example.com",
                "first_name": "John",
                "last_name": "Smith",
            },
            "Parent import field 'student_email' is required.",
        ),
        (
            {
                "email": "parent@example.com",
                "first_name": "John",
                "last_name": "Smith",
                "student_email": "student@example.com",
                "phone": "1" * 51,
            },
            "Parent import field 'phone' cannot exceed 50 characters.",
        ),
    ],
)
@pytest.mark.asyncio
async def test_process_parent_row_defensively_rejects_malformed_rows(
    db_session: AsyncSession,
    row: dict[str, object],
    expected_message: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=expected_message.replace(
            "'",
            r"\'",
        ),
    ):
        await process_parent_row(
            db_session,
            row,
            1,
        )
