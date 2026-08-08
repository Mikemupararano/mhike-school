from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.imports.registry import (
    ImportOptions,
    RowProcessingAction,
    RowProcessingResult,
)
from app.models.user import (
    User,
    UserRole,
    UserStatus,
)
from app.models.user_role import UserRoleAssignment
from app.repositories.parent_student import ParentStudentRepository
from app.repositories.user import UserRepository


def _required_string(
    row: dict[str, Any],
    field_name: str,
) -> str:
    """
    Return a required, trimmed string value from an imported row.

    Validation should normally reject malformed rows before processing.
    These checks protect direct processor calls and defensive code paths.
    """

    value = row.get(
        field_name,
    )

    if value is None:
        raise ValueError(
            f"Parent import field '{field_name}' is required.",
        )

    cleaned = str(
        value,
    ).strip()

    if not cleaned:
        raise ValueError(
            f"Parent import field '{field_name}' cannot be blank.",
        )

    return cleaned


def _optional_string(
    row: dict[str, Any],
    field_name: str,
) -> str | None:
    """
    Return an optional, trimmed string value.
    """

    value = row.get(
        field_name,
    )

    if value is None:
        return None

    cleaned = str(
        value,
    ).strip()

    return cleaned or None


def _normalise_role(
    role: object,
) -> str:
    """
    Return a stable string value for a role enum or string.
    """

    value = getattr(
        role,
        "value",
        role,
    )

    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def _boolean_import_option(
    import_options: ImportOptions,
    field_name: str,
    *,
    default: bool,
) -> bool:
    """
    Return one boolean import option using strict boolean semantics.

    Persisted import options should contain real JSON booleans. Malformed
    values are rejected rather than relying on Python truthiness.
    """

    value = import_options.get(
        field_name,
    )

    if value is None:
        return default

    if not isinstance(
        value,
        bool,
    ):
        raise ValueError(
            f"Import option '{field_name}' must be a boolean.",
        )

    return value


def _should_update_existing_records(
    import_options: ImportOptions | None,
) -> bool:
    """
    Return whether existing records may be modified.

    ``None`` preserves historical behaviour for direct processor calls made
    outside the generic import-batch framework.

    When batch options are supplied, updating existing records is opt-in and
    therefore defaults to False when the option is absent.

    The generic import task reconciles UPDATE and UPSERT operations into this
    option before calling processors.
    """

    if import_options is None:
        return True

    return _boolean_import_option(
        import_options,
        "update_existing_records",
        default=False,
    )


def _has_role_assignment(
    user: User,
    role: UserRole,
) -> bool:
    """
    Return whether the user has the specified persisted role assignment.
    """

    assignments = getattr(
        user,
        "user_roles",
        None,
    )

    if not assignments:
        return False

    return any(
        _normalise_role(
            assignment.role,
        )
        == role.value
        for assignment in assignments
    )


def _is_existing_role(
    user: User,
    role: UserRole,
) -> bool:
    """
    Return whether an account is already recognised as the supplied role.

    Both the authoritative multi-role assignments and the legacy primary-role
    field are considered so legacy accounts can be recognised safely.

    This function performs recognition only. It never grants a role.
    """

    if _has_role_assignment(
        user,
        role,
    ):
        return True

    legacy_role = getattr(
        user,
        "role",
        None,
    )

    return (
        legacy_role is not None
        and _normalise_role(
            legacy_role,
        )
        == role.value
    )


async def _ensure_role_assignment(
    db: AsyncSession,
    *,
    user: User,
    role: UserRole,
) -> bool:
    """
    Ensure the user has the supplied persisted role assignment.

    Returns True when a new assignment was created and False when it already
    existed.

    This helper must only be called after the caller has established that the
    account is legitimately recognised as the requested role. It must not be
    used to convert unrelated accounts implicitly during import.
    """

    if _has_role_assignment(
        user,
        role,
    ):
        return False

    db.add(
        UserRoleAssignment(
            user_id=user.id,
            role=role,
        ),
    )

    await db.flush()

    return True


async def _resolve_student(
    db: AsyncSession,
    *,
    student_email: str,
    school_id: int,
    update_existing_records: bool,
) -> tuple[User, bool]:
    """
    Resolve a student by email within the current school.

    Existing accounts are accepted only when they are already recognised as
    students through either:

    - the authoritative ``user_roles`` assignment table; or
    - the legacy primary ``User.role`` field.

    When updates are enabled, a legitimate legacy student that is missing its
    persisted ``UserRoleAssignment(STUDENT)`` is repaired.

    When updates are disabled, student resolution remains read-only.

    Returns:
        A tuple containing:

        - the resolved student;
        - whether a missing persisted student-role assignment was restored.

    Unrelated users are never converted into students automatically.
    """

    student = await UserRepository(
        db,
    ).get_by_email(
        email=student_email,
        school_id=school_id,
    )

    if student is None:
        raise ValueError(
            f"No student with email '{student_email}' exists in this school.",
        )

    if not _is_existing_role(
        student,
        UserRole.STUDENT,
    ):
        raise ValueError(
            f"The user with email '{student_email}' is not "
            "registered as a student in this school.",
        )

    student_assignment_created = False

    if update_existing_records:
        student_assignment_created = await _ensure_role_assignment(
            db,
            user=student,
            role=UserRole.STUDENT,
        )

        if student_assignment_created:
            await db.flush()

    return (
        student,
        student_assignment_created,
    )


async def _create_or_update_parent(
    db: AsyncSession,
    *,
    email: str,
    first_name: str,
    last_name: str,
    school_id: int,
    update_existing_records: bool,
) -> tuple[
    User,
    RowProcessingAction,
    bool,
]:
    """
    Create, update or reuse one parent account.

    Existing non-parent users are rejected rather than being granted the
    parent role automatically.

    When ``update_existing_records`` is False, an existing recognised parent
    is returned unchanged. No profile fields or role assignments are repaired.

    When updates are allowed, existing parent details are updated and legacy
    parent accounts missing their persisted role assignment are repaired.

    The returned action describes what happened to the parent account itself.

    Returns:
        A tuple containing:

        - the resolved or created parent;
        - the parent-account processing action;
        - whether the parent role assignment was restored.
    """

    repository = UserRepository(
        db,
    )

    existing_user = await repository.get_by_email(
        email=email,
        school_id=school_id,
    )

    full_name = (f"{first_name} {last_name}").strip()

    if existing_user is None:
        parent = User(
            email=email,
            hashed_password=None,
            full_name=full_name,
            role=UserRole.PARENT,
            status=UserStatus.ACTIVE,
            is_active=True,
            school_id=school_id,
        )

        parent = await repository.create(
            parent,
        )

        await _ensure_role_assignment(
            db,
            user=parent,
            role=UserRole.PARENT,
        )

        await db.flush()

        return (
            parent,
            RowProcessingAction.CREATED,
            True,
        )

    if not _is_existing_role(
        existing_user,
        UserRole.PARENT,
    ):
        raise ValueError(
            f"A non-parent user with email '{email}' " "already exists in this school.",
        )

    if not update_existing_records:
        return (
            existing_user,
            RowProcessingAction.SKIPPED,
            False,
        )

    existing_user.email = email
    existing_user.full_name = full_name
    existing_user.status = UserStatus.ACTIVE
    existing_user.is_active = True

    existing_user = await repository.save(
        existing_user,
    )

    assignment_created = await _ensure_role_assignment(
        db,
        user=existing_user,
        role=UserRole.PARENT,
    )

    await db.flush()

    return (
        existing_user,
        RowProcessingAction.UPDATED,
        assignment_created,
    )


def _existing_link_message(
    *,
    parent: User,
    parent_email: str,
    student_email: str,
    parent_action: RowProcessingAction,
    parent_assignment_created: bool,
    student_assignment_created: bool,
) -> str:
    """
    Build an audit message for an already-existing parent/student link.
    """

    parent_name = parent.full_name or parent_email

    if parent_action == RowProcessingAction.UPDATED:
        repairs: list[str] = []

        if parent_assignment_created:
            repairs.append(
                "restored the parent role assignment",
            )

        if student_assignment_created:
            repairs.append(
                "restored the linked student's role assignment",
            )

        if repairs:
            repair_text = " and ".join(
                repairs,
            )

            return (
                f"Updated parent '{parent_name}', {repair_text}, "
                f"but the parent is already linked to student "
                f"'{student_email}'."
            )

        return (
            f"Updated parent '{parent_name}', but the parent is "
            f"already linked to student '{student_email}'."
        )

    if parent_action == RowProcessingAction.SKIPPED:
        return (
            f"Parent '{parent_email}' was left unchanged because updating "
            "existing records is disabled and is already linked "
            f"to student '{student_email}'."
        )

    # Defensive fallback. A newly created parent should not already have
    # an existing relationship, but deterministic behaviour is preferable
    # if repository state ever makes that possible.
    return (
        f"Parent '{parent_email}' is already linked " f"to student '{student_email}'."
    )


def _new_link_message(
    *,
    parent: User,
    parent_email: str,
    student_email: str,
    parent_action: RowProcessingAction,
    parent_assignment_created: bool,
    student_assignment_created: bool,
) -> tuple[str, RowProcessingAction]:
    """
    Build the audit result for a newly-created parent/student link.
    """

    parent_name = parent.full_name or parent_email

    if parent_action == RowProcessingAction.CREATED:
        message = (
            f"Created parent '{parent_name}' and linked "
            f"the parent to student '{student_email}'."
        )

        if student_assignment_created:
            message = (
                f"Created parent '{parent_name}', restored the linked "
                "student's role assignment and linked the parent to "
                f"student '{student_email}'."
            )

        return (
            message,
            RowProcessingAction.CREATED,
        )

    if parent_action == RowProcessingAction.UPDATED:
        repairs: list[str] = []

        if parent_assignment_created:
            repairs.append(
                "restored the parent role assignment",
            )

        if student_assignment_created:
            repairs.append(
                "restored the linked student's role assignment",
            )

        if repairs:
            repair_text = " and ".join(
                repairs,
            )

            message = (
                f"Updated parent '{parent_name}', {repair_text} and linked "
                f"the parent to student '{student_email}'."
            )
        else:
            message = (
                f"Updated parent '{parent_name}' and linked "
                f"the parent to student '{student_email}'."
            )

        return (
            message,
            RowProcessingAction.UPDATED,
        )

    message = (
        f"Left existing parent '{parent_name}' unchanged because updating "
        "existing records is disabled and linked the parent to student "
        f"'{student_email}'."
    )

    # The relationship itself is new, so the row performed a successful
    # create operation even though the existing parent account was not
    # modified.
    return (
        message,
        RowProcessingAction.CREATED,
    )


async def process_parent_row(
    db: AsyncSession,
    row: dict[str, Any],
    school_id: int,
    import_options: ImportOptions | None = None,
) -> RowProcessingResult:
    """
    Create, update or reuse one parent and link the parent to one student.

    Stable import identifiers are used:

    - ``email`` identifies the parent within the current school;
    - ``student_email`` identifies the linked student.

    Existing-record behaviour is controlled by the batch-level
    ``update_existing_records`` option.

    When updates are disabled:

    - a new parent may still be created;
    - an existing recognised parent is not modified;
    - a linked existing student is not modified or role-repaired;
    - an existing parent may still be linked to another student;
    - an existing parent-student relationship remains idempotent and returns
      ``SKIPPED``.

    When updates are enabled:

    - existing parent profile information may be updated;
    - missing parent role assignments may be repaired;
    - a legitimate legacy student missing its persisted student-role
      assignment may be repaired;
    - the required parent-student relationship is created when absent.

    Direct processor calls that omit ``import_options`` retain the historical
    update-existing behaviour for backwards compatibility.

    Existing accounts that are not already recognised as parents or students
    are rejected rather than being converted automatically.

    The optional phone field is validated but is not persisted because the
    current User model does not expose a confirmed phone field.

    Transaction ownership belongs to the generic import service or task.
    This processor therefore flushes changes but never commits or rolls back.
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

    email = _required_string(
        row,
        "email",
    ).lower()

    first_name = _required_string(
        row,
        "first_name",
    )

    last_name = _required_string(
        row,
        "last_name",
    )

    student_email = _required_string(
        row,
        "student_email",
    ).lower()

    phone = _optional_string(
        row,
        "phone",
    )

    if phone is not None and len(phone) > 50:
        raise ValueError(
            "Parent import field 'phone' cannot exceed 50 characters.",
        )

    update_existing_records = _should_update_existing_records(
        import_options,
    )

    student, student_assignment_created = await _resolve_student(
        db,
        student_email=student_email,
        school_id=school_id,
        update_existing_records=update_existing_records,
    )

    (
        parent,
        parent_action,
        parent_assignment_created,
    ) = await _create_or_update_parent(
        db,
        email=email,
        first_name=first_name,
        last_name=last_name,
        school_id=school_id,
        update_existing_records=update_existing_records,
    )

    link_repository = ParentStudentRepository(
        db,
    )

    existing_link = await link_repository.get_link_in_school(
        parent_id=parent.id,
        student_id=student.id,
        school_id=school_id,
        include_relationships=False,
    )

    # ------------------------------------------------------------------
    # Existing relationship: idempotent relationship no-op.
    #
    # Account repairs may already have occurred when updates are enabled.
    # The relationship itself remains SKIPPED because it already exists.
    # ------------------------------------------------------------------

    if existing_link is not None:
        message = _existing_link_message(
            parent=parent,
            parent_email=email,
            student_email=student_email,
            parent_action=parent_action,
            parent_assignment_created=parent_assignment_created,
            student_assignment_created=student_assignment_created,
        )

        return RowProcessingResult(
            action=RowProcessingAction.SKIPPED,
            entity_id=existing_link.id,
            message=message,
        )

    # ------------------------------------------------------------------
    # Relationship does not yet exist: create it.
    # ------------------------------------------------------------------

    link = await link_repository.create_link(
        parent_id=parent.id,
        student_id=student.id,
    )

    await db.flush()

    message, result_action = _new_link_message(
        parent=parent,
        parent_email=email,
        student_email=student_email,
        parent_action=parent_action,
        parent_assignment_created=parent_assignment_created,
        student_assignment_created=student_assignment_created,
    )

    return RowProcessingResult(
        action=result_action,
        entity_id=link.id,
        message=message,
    )
