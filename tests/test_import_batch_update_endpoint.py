from __future__ import annotations

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.import_batch import (
    ImportBatch,
    ImportOperation,
    ImportStatus,
)
from app.models.user import User

pytestmark = pytest.mark.asyncio


EDITABLE_BATCH_STATUSES = (ImportStatus.UPLOADED,)

LOCKED_BATCH_STATUSES = (
    ImportStatus.PARSING,
    ImportStatus.VALIDATING,
    ImportStatus.READY,
    ImportStatus.QUEUED,
    ImportStatus.PROCESSING,
    ImportStatus.COMPLETED,
    ImportStatus.COMPLETED_WITH_ERRORS,
    ImportStatus.FAILED,
    ImportStatus.CANCELLED,
)


def _assert_http_error(
    response: Response,
    *,
    status_code: int,
    message: str,
) -> None:
    """Assert the application's standard HTTP error envelope."""

    assert response.status_code == status_code

    assert response.json() == {
        "success": False,
        "error": {
            "code": "HTTP_ERROR",
            "message": message,
        },
    }


async def _create_batch(
    db_session: AsyncSession,
    *,
    school_id: int,
    uploaded_by_id: int,
    status: ImportStatus = ImportStatus.UPLOADED,
    is_archived: bool = False,
    column_mapping: dict[str, object] | None = None,
    import_options: dict[str, object] | None = None,
) -> ImportBatch:
    """Create a persisted batch suitable for endpoint tests."""

    batch = ImportBatch(
        school_id=school_id,
        uploaded_by_id=uploaded_by_id,
        import_type="students",
        operation=ImportOperation.CREATE,
        status=status,
        original_filename="students.csv",
        column_mapping=column_mapping or {},
        import_options=import_options or {},
        validation_summary={},
        result_summary={},
        is_archived=is_archived,
    )

    db_session.add(batch)
    await db_session.commit()
    await db_session.refresh(batch)

    return batch


async def test_school_admin_can_update_column_mapping(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user: User,
    auth_headers,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    batch = await _create_batch(
        db_session,
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    payload = {
        "column_mapping": {
            "uploaded_headers": [
                "Email Address",
                "First Name",
                "Surname",
            ],
            "detected_headers": [
                "email_address",
                "first_name",
                "surname",
            ],
            "mapping": {
                "email_address": "email",
                "first_name": "first_name",
                "surname": "last_name",
            },
            "mapping_completed": True,
        },
    }

    response = await client.patch(
        f"/api/v1/import-batches/{batch.id}",
        json=payload,
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    response_payload = response.json()

    assert response_payload["id"] == batch.id
    assert response_payload["school_id"] == school_id
    assert response_payload["column_mapping"] == payload["column_mapping"]

    await db_session.refresh(batch)

    assert batch.column_mapping == payload["column_mapping"]


async def test_school_admin_can_update_import_options(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user: User,
    auth_headers,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    batch = await _create_batch(
        db_session,
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    payload = {
        "import_options": {
            "skip_duplicate_rows": True,
            "update_existing_records": False,
            "send_account_notifications": True,
        },
    }

    response = await client.patch(
        f"/api/v1/import-batches/{batch.id}",
        json=payload,
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200
    assert response.json()["import_options"] == payload["import_options"]

    await db_session.refresh(batch)

    assert batch.import_options == payload["import_options"]


async def test_partial_update_preserves_omitted_fields(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user: User,
    auth_headers,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    original_mapping = {
        "mapping": {
            "email_address": "email",
        },
    }

    original_options = {
        "skip_duplicate_rows": False,
    }

    batch = await _create_batch(
        db_session,
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        column_mapping=original_mapping,
        import_options=original_options,
    )

    response = await client.patch(
        f"/api/v1/import-batches/{batch.id}",
        json={
            "import_options": {
                "skip_duplicate_rows": True,
            },
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["column_mapping"] == original_mapping
    assert payload["import_options"] == {
        "skip_duplicate_rows": True,
    }

    await db_session.refresh(batch)

    assert batch.column_mapping == original_mapping
    assert batch.import_options == {
        "skip_duplicate_rows": True,
    }


@pytest.mark.parametrize(
    "batch_status",
    EDITABLE_BATCH_STATUSES,
)
async def test_uploaded_batch_can_be_updated(
    batch_status: ImportStatus,
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user: User,
    auth_headers,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    batch = await _create_batch(
        db_session,
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        status=batch_status,
    )

    response = await client.patch(
        f"/api/v1/import-batches/{batch.id}",
        json={
            "column_mapping": {
                "mapping_completed": False,
            },
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "batch_status",
    LOCKED_BATCH_STATUSES,
)
async def test_batch_cannot_be_updated_after_validation_has_started(
    batch_status: ImportStatus,
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user: User,
    auth_headers,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    batch = await _create_batch(
        db_session,
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        status=batch_status,
    )

    response = await client.patch(
        f"/api/v1/import-batches/{batch.id}",
        json={
            "column_mapping": {
                "mapping_completed": True,
            },
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    _assert_http_error(
        response,
        status_code=409,
        message=(
            "Import batch configuration can only be updated while "
            "the batch has status 'uploaded'. Current status: "
            f"'{batch_status.value}'."
        ),
    )


async def test_archived_batch_cannot_be_updated(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user: User,
    auth_headers,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    batch = await _create_batch(
        db_session,
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        is_archived=True,
    )

    response = await client.patch(
        f"/api/v1/import-batches/{batch.id}",
        json={
            "import_options": {
                "skip_duplicate_rows": True,
            },
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    _assert_http_error(
        response,
        status_code=409,
        message="Archived import batches cannot be updated.",
    )


async def test_school_admin_cannot_update_batch_from_another_school(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user: User,
    auth_headers,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    batch = await _create_batch(
        db_session,
        school_id=school_id + 1,
        uploaded_by_id=school_admin_user.id,
    )

    response = await client.patch(
        f"/api/v1/import-batches/{batch.id}",
        json={
            "column_mapping": {
                "mapping_completed": True,
            },
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    _assert_http_error(
        response,
        status_code=404,
        message="Import batch not found.",
    )


async def test_non_import_admin_cannot_update_batch(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user: User,
    student_user: User,
    auth_headers,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    batch = await _create_batch(
        db_session,
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    response = await client.patch(
        f"/api/v1/import-batches/{batch.id}",
        json={
            "column_mapping": {
                "mapping_completed": True,
            },
        },
        headers=auth_headers(
            student_user,
        ),
    )

    _assert_http_error(
        response,
        status_code=403,
        message=(
            "Only school administrators or platform administrators "
            "can manage imports."
        ),
    )


async def test_unauthenticated_user_cannot_update_batch(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user: User,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    batch = await _create_batch(
        db_session,
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    response = await client.patch(
        f"/api/v1/import-batches/{batch.id}",
        json={
            "column_mapping": {
                "mapping_completed": True,
            },
        },
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    (
        "protected_field",
        "protected_value",
    ),
    [
        (
            "school_id",
            999,
        ),
        (
            "uploaded_by_id",
            999,
        ),
        (
            "status",
            "completed",
        ),
        (
            "total_rows",
            999,
        ),
        (
            "successful_rows",
            999,
        ),
        (
            "created_at",
            "2026-08-04T12:00:00Z",
        ),
        (
            "is_archived",
            True,
        ),
    ],
)
async def test_system_controlled_fields_are_rejected(
    protected_field: str,
    protected_value: object,
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user: User,
    auth_headers,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    batch = await _create_batch(
        db_session,
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    response = await client.patch(
        f"/api/v1/import-batches/{batch.id}",
        json={
            protected_field: protected_value,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 422


async def test_empty_update_payload_is_accepted_as_no_op(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user: User,
    auth_headers,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    original_mapping = {
        "mapping_completed": False,
    }

    original_options = {
        "skip_duplicate_rows": False,
    }

    batch = await _create_batch(
        db_session,
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
        column_mapping=original_mapping,
        import_options=original_options,
    )

    response = await client.patch(
        f"/api/v1/import-batches/{batch.id}",
        json={},
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["column_mapping"] == original_mapping
    assert payload["import_options"] == original_options


async def test_patch_batch_route_is_not_treated_as_an_action_route(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user: User,
    auth_headers,
) -> None:
    school_id = school_admin_user.school_id

    assert school_id is not None

    batch = await _create_batch(
        db_session,
        school_id=school_id,
        uploaded_by_id=school_admin_user.id,
    )

    response = await client.patch(
        f"/api/v1/import-batches/{batch.id}",
        json={
            "column_mapping": {
                "mapping_completed": True,
            },
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200
    assert response.json()["id"] == batch.id
