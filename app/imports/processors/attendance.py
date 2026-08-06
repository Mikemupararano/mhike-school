from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.imports.registry import (
    RowProcessingAction,
    RowProcessingResult,
)
from app.models.attendance_record import AttendanceStatus
from app.models.attendance_session import AttendanceSessionType
from app.models.class_group import ClassGroup
from app.models.user import User, UserRole
from app.repositories.attendance import AttendanceRepository
from app.repositories.class_group import ClassGroupRepository
from app.repositories.user import UserRepository
from app.schemas.attendance import (
    AttendanceRecordCreate,
    AttendanceRecordUpdate,
)


def _required_string(
    row: dict[str, Any],
    field_name: str,
    *,
    max_length: int | None = None,
) -> str:
    """
    Return a required, trimmed string value.
    """

    value = row.get(field_name)

    if value is None:
        raise ValueError(
            f"Attendance import field '{field_name}' is required.",
        )

    cleaned = str(value).strip()

    if not cleaned:
        raise ValueError(
            f"Attendance import field '{field_name}' cannot be blank.",
        )

    if max_length is not None and len(cleaned) > max_length:
        raise ValueError(
            f"Attendance import field '{field_name}' cannot exceed "
            f"{max_length} characters.",
        )

    return cleaned


def _optional_string(
    row: dict[str, Any],
    field_name: str,
    *,
    max_length: int | None = None,
) -> str | None:
    """
    Return a trimmed optional string.

    Blank values are normalised to None.
    """

    value = row.get(field_name)

    if value is None:
        return None

    cleaned = str(value).strip()

    if not cleaned:
        return None

    if max_length is not None and len(cleaned) > max_length:
        raise ValueError(
            f"Attendance import field '{field_name}' cannot exceed "
            f"{max_length} characters.",
        )

    return cleaned


def _required_date(
    row: dict[str, Any],
    field_name: str,
) -> date:
    """
    Return a required ISO date value.
    """

    value = row.get(
        field_name,
    )

    if isinstance(
        value,
        datetime,
    ):
        return value.date()

    if isinstance(
        value,
        date,
    ):
        return value

    if isinstance(value, str):
        cleaned = value.strip()

        if cleaned:
            try:
                return date.fromisoformat(cleaned)
            except ValueError:
                pass

    raise ValueError(
        f"Attendance import field '{field_name}' " "must be a valid ISO date.",
    )


def _required_session_type(
    row: dict[str, Any],
) -> AttendanceSessionType:
    """
    Return a validated attendance session type.
    """

    value = row.get("session_type")

    if isinstance(value, AttendanceSessionType):
        return value

    if isinstance(value, str):
        cleaned = value.strip().lower()

        try:
            return AttendanceSessionType(cleaned)
        except ValueError:
            pass

    raise ValueError(
        "Attendance import field 'session_type' must be one of: am, pm.",
    )


def _required_status(
    row: dict[str, Any],
) -> AttendanceStatus:
    """
    Return a validated attendance status.
    """

    value = row.get("status")

    if isinstance(value, AttendanceStatus):
        return value

    if isinstance(value, str):
        cleaned = value.strip().lower()

        try:
            return AttendanceStatus(cleaned)
        except ValueError:
            pass

    raise ValueError(
        "Attendance import field 'status' must be one of: "
        "present, late, authorised_absence, unauthorised_absence.",
    )


def _validate_school_id(
    school_id: int,
) -> None:
    """
    Require a positive integer school identifier.

    Boolean values are rejected explicitly because ``bool`` is a subclass
    of ``int`` in Python.
    """

    if (
        not isinstance(
            school_id,
            int,
        )
        or isinstance(
            school_id,
            bool,
        )
        or school_id < 1
    ):
        raise ValueError(
            "school_id must be a positive integer.",
        )


def _normalise_email(
    value: str,
    field_name: str,
) -> str:
    """
    Return a required, lowercase email address.
    """

    cleaned = value.strip().lower()

    if not cleaned:
        raise ValueError(
            f"Attendance import field '{field_name}' cannot be blank.",
        )

    return cleaned


def _is_authorised_marker(
    user: User,
) -> bool:
    """
    Return whether a user may mark attendance.
    """

    return any(
        user.has_role(role)
        for role in {
            UserRole.TEACHER,
            UserRole.SCHOOL_ADMIN,
            UserRole.PLATFORM_ADMIN,
        }
    )


async def _resolve_class_group(
    db: AsyncSession,
    *,
    class_name: str,
    school_id: int,
) -> ClassGroup:
    """
    Resolve a class group within the current school.
    """

    class_group = await ClassGroupRepository(
        db,
    ).get_by_name_and_school(
        name=class_name,
        school_id=school_id,
        include_relationships=False,
    )

    if class_group is None:
        raise ValueError(
            f"No class named '{class_name}' exists in this school.",
        )

    return class_group


async def _resolve_student(
    db: AsyncSession,
    *,
    student_email: str,
    school_id: int,
) -> User:
    """
    Resolve and role-check the student.
    """

    normalised_email = _normalise_email(
        student_email,
        "student_email",
    )

    student = await UserRepository(
        db,
    ).get_by_email(
        email=normalised_email,
        school_id=school_id,
    )

    if student is None:
        raise ValueError(
            f"No student with email '{normalised_email}' exists " "in this school.",
        )

    if not student.has_role(UserRole.STUDENT):
        raise ValueError(
            f"The user with email '{normalised_email}' is not "
            "registered as a student in this school.",
        )

    return student


async def _resolve_marker(
    db: AsyncSession,
    *,
    marked_by_email: str | None,
    school_id: int,
) -> User | None:
    """
    Resolve and permission-check the optional attendance marker.
    """

    if marked_by_email is None:
        return None

    normalised_email = _normalise_email(
        marked_by_email,
        "marked_by_email",
    )

    marker = await UserRepository(
        db,
    ).get_by_email(
        email=normalised_email,
        school_id=school_id,
    )

    if marker is None:
        raise ValueError(
            f"No attendance marker with email '{normalised_email}' exists "
            "in this school.",
        )

    if not _is_authorised_marker(marker):
        raise ValueError(
            f"The user with email '{normalised_email}' is not authorised "
            "to mark attendance.",
        )

    return marker


async def process_attendance_row(
    db: AsyncSession,
    row: dict[str, Any],
    school_id: int,
) -> RowProcessingResult:
    """
    Create or update one attendance record from validated import data.

    Sessions are resolved using the school-scoped natural key:

    - ``school_id``;
    - ``class_group_id``;
    - ``session_date``;
    - ``session_type``.

    Attendance records are matched using:

    - ``attendance_session_id``;
    - ``student_id``.

    The repository contract intentionally uses ``AttendanceRecordCreate``
    for creation and ``AttendanceRecordUpdate`` for updates.

    Transaction ownership belongs to the generic import service or
    background task. This processor never commits or rolls back the session.
    """

    _validate_school_id(
        school_id,
    )

    class_name = _required_string(
        row,
        "class_name",
        max_length=255,
    )

    session_date = _required_date(
        row,
        "session_date",
    )

    session_type = _required_session_type(
        row,
    )

    student_email = _required_string(
        row,
        "student_email",
        max_length=320,
    )

    status = _required_status(
        row,
    )

    marked_by_email = _optional_string(
        row,
        "marked_by_email",
        max_length=320,
    )

    notes = _optional_string(
        row,
        "notes",
        max_length=500,
    )

    class_group = await _resolve_class_group(
        db,
        class_name=class_name,
        school_id=school_id,
    )

    student = await _resolve_student(
        db,
        student_email=student_email,
        school_id=school_id,
    )

    marker = await _resolve_marker(
        db,
        marked_by_email=marked_by_email,
        school_id=school_id,
    )

    repository = AttendanceRepository(
        db,
    )

    session = await repository.get_existing_session(
        school_id=school_id,
        class_group_id=class_group.id,
        session_date=session_date,
        session_type=session_type,
    )

    if session is None:
        raise ValueError(
            f"No {session_type.value.upper()} attendance session exists "
            f"for class '{class_name}' on {session_date.isoformat()}.",
        )

    existing_record = await repository.get_record_by_session_and_student(
        attendance_session_id=session.id,
        student_id=student.id,
    )

    if existing_record is None:
        record = await repository.create_record(
            AttendanceRecordCreate(
                attendance_session_id=session.id,
                student_id=student.id,
                status=status,
                marked_by_id=(marker.id if marker is not None else None),
                notes=notes,
            ),
        )

        return RowProcessingResult(
            action=RowProcessingAction.CREATED,
            entity_id=record.id,
            message=(
                f"Created {session_type.value.upper()} attendance record "
                f"for '{student.email}' on {session_date.isoformat()}."
            ),
        )

    record = await repository.update_record(
        existing_record,
        AttendanceRecordUpdate(
            status=status,
            marked_by_id=(marker.id if marker is not None else None),
            notes=notes,
        ),
    )

    return RowProcessingResult(
        action=RowProcessingAction.UPDATED,
        entity_id=record.id,
        message=(
            f"Updated {session_type.value.upper()} attendance record "
            f"for '{student.email}' on {session_date.isoformat()}."
        ),
    )
