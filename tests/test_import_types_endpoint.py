from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.imports.registry import registered_import_types
from app.models.user import User


@pytest.mark.asyncio
async def test_school_admin_can_list_supported_import_types(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        "/api/v1/import-batches/types",
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    payload = response.json()

    assert isinstance(payload, list)
    assert payload

    values = [item["value"] for item in payload]

    assert values == registered_import_types()

    assert all(
        isinstance(
            item["label"],
            str,
        )
        and item["label"].strip()
        for item in payload
    )

    assert all(item.get("description") is None for item in payload)


@pytest.mark.asyncio
async def test_supported_import_types_are_sorted(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        "/api/v1/import-batches/types",
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    values = [item["value"] for item in response.json()]

    assert values == sorted(
        values,
    )


@pytest.mark.asyncio
async def test_supported_import_types_include_recent_handlers(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        "/api/v1/import-batches/types",
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    values = {item["value"] for item in response.json()}

    assert {
        "assignments",
        "assignment_submissions",
        "attendance",
        "timetable_assignments",
        "timetable_entries",
        "timetable_periods",
    }.issubset(
        values,
    )


@pytest.mark.asyncio
async def test_supported_import_types_exclude_unregistered_placeholders(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        "/api/v1/import-batches/types",
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    values = {item["value"] for item in response.json()}

    assert "staff" not in values
    assert "subjects" not in values
    assert "teaching_assignments" not in values
    assert "marks" not in values


@pytest.mark.asyncio
async def test_non_import_admin_cannot_list_supported_import_types(
    client: AsyncClient,
    student_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        "/api/v1/import-batches/types",
        headers=auth_headers(
            student_user,
        ),
    )

    assert response.status_code == 403

    payload = response.json()

    assert (
        "Only school administrators or platform administrators " "can manage imports."
    ) in str(
        payload,
    )


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_list_supported_import_types(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/import-batches/types",
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_types_route_is_not_treated_as_batch_id(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        "/api/v1/import-batches/types",
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    payload = response.json()

    assert isinstance(
        payload,
        list,
    )

    assert all("value" in item and "label" in item for item in payload)
