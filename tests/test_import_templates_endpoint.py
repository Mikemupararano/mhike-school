from __future__ import annotations

import csv
import io

import pytest
from httpx import AsyncClient, Response

from app.imports.registry import registered_import_types
from app.models.user import User
from app.services.import_template_service import (
    generate_import_template_csv,
    get_import_template_metadata,
    list_import_template_summaries,
)


def _assert_http_error(
    response: Response,
    *,
    status_code: int,
    message: str,
) -> None:
    """Assert the application's standard HTTP error response envelope."""

    assert response.status_code == status_code

    assert response.json() == {
        "success": False,
        "error": {
            "code": "HTTP_ERROR",
            "message": message,
        },
    }


@pytest.mark.asyncio
async def test_school_admin_can_list_import_templates(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        "/api/v1/import-batches/templates",
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    payload = response.json()
    expected = list_import_template_summaries()

    assert isinstance(payload, dict)
    assert payload["total"] == expected.total
    assert payload["total"] == len(
        registered_import_types(),
    )
    assert payload["total"] == 13

    assert isinstance(
        payload["items"],
        list,
    )
    assert len(payload["items"]) == payload["total"]


@pytest.mark.asyncio
async def test_import_template_summaries_match_service_output(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        "/api/v1/import-batches/templates",
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    assert response.json() == (
        list_import_template_summaries().model_dump(
            mode="json",
        )
    )


@pytest.mark.asyncio
async def test_import_template_summaries_are_sorted(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        "/api/v1/import-batches/templates",
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    import_types = [item["import_type"] for item in response.json()["items"]]

    assert import_types == sorted(
        import_types,
    )
    assert import_types == registered_import_types()


@pytest.mark.asyncio
async def test_template_summary_contains_counts_and_urls(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        "/api/v1/import-batches/templates",
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    attendance = next(
        item for item in response.json()["items"] if item["import_type"] == "attendance"
    )

    assert attendance == {
        "import_type": "attendance",
        "display_name": "Attendance",
        "description": (
            "Import student attendance records for lessons, " "sessions or school days."
        ),
        "required_field_count": 5,
        "optional_field_count": 2,
        "total_field_count": 7,
        "metadata_url": ("/api/v1/import-batches/templates/attendance"),
        "download_url": ("/api/v1/import-batches/templates/" "attendance/download"),
    }


@pytest.mark.asyncio
async def test_school_admin_can_get_attendance_template_metadata(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        "/api/v1/import-batches/templates/attendance",
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    payload = response.json()
    expected = get_import_template_metadata(
        "attendance",
    )

    assert payload == expected.model_dump(
        mode="json",
    )


@pytest.mark.asyncio
async def test_attendance_template_metadata_contains_expected_fields(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        "/api/v1/import-batches/templates/attendance",
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["import_type"] == "attendance"
    assert payload["display_name"] == "Attendance"
    assert payload["schema_name"] == "AttendanceImportSchema"

    assert payload["csv_headers"] == [
        "class_name",
        "session_date",
        "session_type",
        "student_email",
        "status",
        "marked_by_email",
        "notes",
    ]

    assert [field["name"] for field in payload["required_fields"]] == [
        "class_name",
        "session_date",
        "session_type",
        "student_email",
        "status",
    ]

    assert [field["name"] for field in payload["optional_fields"]] == [
        "marked_by_email",
        "notes",
    ]


@pytest.mark.asyncio
async def test_attendance_template_metadata_exposes_examples(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        "/api/v1/import-batches/templates/attendance",
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    assert response.json()["sample_row"] == {
        "class_name": "Year 10 Physics",
        "session_date": "2026-08-04",
        "session_type": "am",
        "student_email": "student@example.com",
        "status": "present",
        "marked_by_email": "teacher@example.com",
        "notes": ("Arrived 10 minutes late due to transport " "disruption."),
    }


@pytest.mark.asyncio
async def test_attendance_template_metadata_exposes_enum_fields(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        "/api/v1/import-batches/templates/attendance",
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    fields = {field["name"]: field for field in response.json()["fields"]}

    assert fields["session_type"]["data_type"] == "enum"
    assert fields["session_type"]["accepted_values"] == [
        "am",
        "pm",
    ]

    assert fields["status"]["data_type"] == "enum"
    assert fields["status"]["accepted_values"] == [
        "present",
        "late",
        "authorised_absence",
        "unauthorised_absence",
    ]


@pytest.mark.asyncio
async def test_unknown_template_metadata_returns_404(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        ("/api/v1/import-batches/templates/" "unknown_import_type"),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    _assert_http_error(
        response,
        status_code=404,
        message=("Import type 'unknown_import_type' is not registered."),
    )


@pytest.mark.asyncio
async def test_school_admin_can_preview_import_template(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        ("/api/v1/import-batches/templates/" "attendance/preview"),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["import_type"] == "attendance"
    assert payload["filename"] == ("attendance_import_template.csv")
    assert payload["content_type"] == "text/csv"

    assert payload["csv_content"] == (
        generate_import_template_csv(
            "attendance",
        )
    )


@pytest.mark.asyncio
async def test_preview_includes_sample_row_by_default(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        ("/api/v1/import-batches/templates/" "attendance/preview"),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    rows = list(
        csv.reader(
            io.StringIO(
                response.json()["csv_content"],
            ),
        ),
    )

    assert len(rows) == 2

    assert rows[0] == [
        "class_name",
        "session_date",
        "session_type",
        "student_email",
        "status",
        "marked_by_email",
        "notes",
    ]

    assert rows[1] == [
        "Year 10 Physics",
        "2026-08-04",
        "am",
        "student@example.com",
        "present",
        "teacher@example.com",
        ("Arrived 10 minutes late due to transport " "disruption."),
    ]


@pytest.mark.asyncio
async def test_preview_can_exclude_sample_row(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        ("/api/v1/import-batches/templates/" "attendance/preview"),
        params={
            "include_sample_row": False,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["csv_content"] == (
        generate_import_template_csv(
            "attendance",
            include_sample_row=False,
        )
    )

    rows = list(
        csv.reader(
            io.StringIO(
                payload["csv_content"],
            ),
        ),
    )

    assert len(rows) == 1


@pytest.mark.asyncio
async def test_unknown_template_preview_returns_404(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        ("/api/v1/import-batches/templates/" "unknown_import_type/preview"),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    _assert_http_error(
        response,
        status_code=404,
        message=("Import type 'unknown_import_type' is not registered."),
    )


@pytest.mark.asyncio
async def test_school_admin_can_download_import_template(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        ("/api/v1/import-batches/templates/" "attendance/download"),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    assert response.headers["content-type"].startswith(
        "text/csv",
    )

    assert response.headers["content-disposition"] == (
        'attachment; filename="' 'attendance_import_template.csv"'
    )

    assert response.headers["x-content-type-options"] == ("nosniff")


@pytest.mark.asyncio
async def test_downloaded_template_contains_utf8_bom(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        ("/api/v1/import-batches/templates/" "attendance/download"),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    assert response.content.startswith(
        b"\xef\xbb\xbf",
    )


@pytest.mark.asyncio
async def test_downloaded_template_matches_generated_csv(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        ("/api/v1/import-batches/templates/" "attendance/download"),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    downloaded_csv = response.content.decode(
        "utf-8-sig",
    )

    assert downloaded_csv == generate_import_template_csv(
        "attendance",
    )


@pytest.mark.asyncio
async def test_download_can_exclude_sample_row(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        ("/api/v1/import-batches/templates/" "attendance/download"),
        params={
            "include_sample_row": False,
        },
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    downloaded_csv = response.content.decode(
        "utf-8-sig",
    )

    assert downloaded_csv == generate_import_template_csv(
        "attendance",
        include_sample_row=False,
    )

    rows = list(
        csv.reader(
            io.StringIO(
                downloaded_csv,
            ),
        ),
    )

    assert len(rows) == 1


@pytest.mark.asyncio
async def test_unknown_template_download_returns_404(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        ("/api/v1/import-batches/templates/" "unknown_import_type/download"),
        headers=auth_headers(
            school_admin_user,
        ),
    )

    _assert_http_error(
        response,
        status_code=404,
        message=("Import type 'unknown_import_type' is not registered."),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/import-batches/templates",
        ("/api/v1/import-batches/templates/" "attendance"),
        ("/api/v1/import-batches/templates/" "attendance/preview"),
        ("/api/v1/import-batches/templates/" "attendance/download"),
    ],
)
async def test_non_import_admin_cannot_access_template_routes(
    path: str,
    client: AsyncClient,
    student_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        path,
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/import-batches/templates",
        ("/api/v1/import-batches/templates/" "attendance"),
        ("/api/v1/import-batches/templates/" "attendance/preview"),
        ("/api/v1/import-batches/templates/" "attendance/download"),
    ],
)
async def test_unauthenticated_user_cannot_access_template_routes(
    path: str,
    client: AsyncClient,
) -> None:
    response = await client.get(
        path,
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_templates_route_is_not_treated_as_batch_id(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        "/api/v1/import-batches/templates",
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    payload = response.json()

    assert isinstance(
        payload,
        dict,
    )
    assert "items" in payload
    assert "total" in payload


@pytest.mark.asyncio
async def test_template_metadata_route_is_not_treated_as_batch_id(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    response = await client.get(
        "/api/v1/import-batches/templates/students",
        headers=auth_headers(
            school_admin_user,
        ),
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["import_type"] == "students"
    assert payload["schema_name"] == "StudentImportSchema"


@pytest.mark.asyncio
async def test_every_registered_template_metadata_route_is_available(
    client: AsyncClient,
    school_admin_user: User,
    auth_headers,
) -> None:
    for import_type in registered_import_types():
        response = await client.get(
            ("/api/v1/import-batches/templates/" f"{import_type}"),
            headers=auth_headers(
                school_admin_user,
            ),
        )

        assert response.status_code == 200
        assert response.json()["import_type"] == import_type
