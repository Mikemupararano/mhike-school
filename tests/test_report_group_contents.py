from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.class_group import ClassGroup
from app.models.report_group_content import ReportGroupContent
from app.models.report_session import ReportSession


BASE_URL = "/api/v1/report-group-contents"


def _error_message(response) -> str:
    """
    Extract the API error message from the project's standard error envelope.

    The application currently returns errors in this form:

        {
            "success": False,
            "error": {
                "code": "...",
                "message": "..."
            }
        }

    FastAPI's default ``detail`` shape is also supported so these tests remain
    resilient if the exception handler changes later.
    """

    body = response.json()

    detail = body.get("detail")
    if isinstance(detail, str):
        return detail

    message = body.get("message")
    if isinstance(message, str):
        return message

    error = body.get("error")

    if isinstance(error, str):
        return error

    if isinstance(error, dict):
        nested_message = error.get("message")
        if isinstance(nested_message, str):
            return nested_message

        nested_detail = error.get("detail")
        if isinstance(nested_detail, str):
            return nested_detail

    raise AssertionError(
        f"Could not extract an error message from response body: {body!r}"
    )


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


async def _create_report_session(
    db: AsyncSession,
    *,
    school_id: int,
    title: str = "Autumn Reports",
) -> ReportSession:
    """
    Create a valid reporting session for shared-content endpoint tests.

    Include and require fields are populated dynamically so the helper remains
    compatible when new configurable report fields are added to the model.
    """

    values: dict[str, object] = {
        "school_id": school_id,
        "title": title,
        "academic_year": "2026/27",
        "term": "Autumn",
        "checkpoint_name": "Autumn Reports",
        "reporting_mode": "full_report",
        "active": True,
    }

    for column in ReportSession.__table__.columns:
        if column.name.startswith("include_"):
            values[column.name] = True

        if column.name.startswith("require_"):
            values[column.name] = False

        if column.name.startswith("show_previous_"):
            values[column.name] = False

    report_session = ReportSession(**values)

    db.add(report_session)
    await db.commit()
    await db.refresh(report_session)

    return report_session


async def _create_class_group(
    db: AsyncSession,
    *,
    school_id: int,
    teacher_id: int | None,
    name: str = "10A Science",
) -> ClassGroup:
    """Create one school-scoped class group."""

    class_group = ClassGroup(
        school_id=school_id,
        teacher_id=teacher_id,
        name=name,
    )

    db.add(class_group)
    await db.commit()
    await db.refresh(class_group)

    return class_group


async def _create_shared_content(
    db: AsyncSession,
    *,
    school_id: int,
    report_session_id: int,
    class_group_id: int,
    subject_name: str = "Chemistry",
    work_covered: str = "Rates of reaction and reversible reactions.",
    updated_by_id: int | None = None,
) -> ReportGroupContent:
    """Create one shared-content record directly in the database."""

    record = ReportGroupContent(
        school_id=school_id,
        report_session_id=report_session_id,
        class_group_id=class_group_id,
        subject_name=subject_name,
        work_covered=work_covered,
        updated_by_id=updated_by_id,
    )

    db.add(record)
    await db.commit()
    await db.refresh(record)

    return record


# ----------------------------------------------------------------------
# Upsert permissions and behaviour
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assigned_teacher_can_create_shared_content(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    report_session = await _create_report_session(
        db_session,
        school_id=teacher_user.school_id,
    )

    class_group = await _create_class_group(
        db_session,
        school_id=teacher_user.school_id,
        teacher_id=teacher_user.id,
    )

    response = await client.put(
        f"{BASE_URL}/",
        json={
            "report_session_id": report_session.id,
            "class_group_id": class_group.id,
            "subject_name": "  Chemistry  ",
            "work_covered": (
                "  Rates of reaction, reversible reactions and equilibrium.  "
            ),
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200

    body = response.json()

    assert body["school_id"] == teacher_user.school_id
    assert body["report_session_id"] == report_session.id
    assert body["class_group_id"] == class_group.id
    assert body["subject_name"] == "Chemistry"
    assert (
        body["work_covered"]
        == "Rates of reaction, reversible reactions and equilibrium."
    )
    assert body["updated_by_id"] == teacher_user.id
    assert body["id"] >= 1
    assert body["created_at"] is not None
    assert body["updated_at"] is not None


@pytest.mark.asyncio
async def test_upsert_updates_existing_scope_without_creating_duplicate(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    report_session = await _create_report_session(
        db_session,
        school_id=teacher_user.school_id,
    )

    class_group = await _create_class_group(
        db_session,
        school_id=teacher_user.school_id,
        teacher_id=teacher_user.id,
    )

    payload = {
        "report_session_id": report_session.id,
        "class_group_id": class_group.id,
        "subject_name": "Physics",
        "work_covered": "Forces and motion.",
    }

    first_response = await client.put(
        f"{BASE_URL}/",
        json=payload,
        headers=auth_headers(teacher_user),
    )

    assert first_response.status_code == 200

    first_body = first_response.json()

    payload["work_covered"] = "Forces, motion, momentum and energy."

    second_response = await client.put(
        f"{BASE_URL}/",
        json=payload,
        headers=auth_headers(teacher_user),
    )

    assert second_response.status_code == 200

    second_body = second_response.json()

    assert second_body["id"] == first_body["id"]
    assert second_body["work_covered"] == (
        "Forces, motion, momentum and energy."
    )

    count_result = await db_session.execute(
        select(func.count(ReportGroupContent.id)).where(
            ReportGroupContent.school_id == teacher_user.school_id,
            ReportGroupContent.report_session_id == report_session.id,
            ReportGroupContent.class_group_id == class_group.id,
            ReportGroupContent.subject_name == "Physics",
        )
    )

    assert count_result.scalar_one() == 1


@pytest.mark.asyncio
async def test_teacher_cannot_manage_unassigned_class_content(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    school_admin_user,
    auth_headers,
):
    report_session = await _create_report_session(
        db_session,
        school_id=teacher_user.school_id,
    )

    class_group = await _create_class_group(
        db_session,
        school_id=teacher_user.school_id,
        teacher_id=school_admin_user.id,
    )

    response = await client.put(
        f"{BASE_URL}/",
        json={
            "report_session_id": report_session.id,
            "class_group_id": class_group.id,
            "subject_name": "Biology",
            "work_covered": "Cell biology.",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 403
    assert _error_message(response) == (
        "Only the assigned class teacher, School Admin or Platform Admin "
        "can manage shared report content for this class."
    )


@pytest.mark.asyncio
async def test_school_admin_can_manage_content_for_any_school_class(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    teacher_user,
    auth_headers,
):
    report_session = await _create_report_session(
        db_session,
        school_id=school_admin_user.school_id,
    )

    class_group = await _create_class_group(
        db_session,
        school_id=school_admin_user.school_id,
        teacher_id=teacher_user.id,
    )

    response = await client.put(
        f"{BASE_URL}/",
        json={
            "report_session_id": report_session.id,
            "class_group_id": class_group.id,
            "subject_name": "English",
            "work_covered": "Shakespeare and creative writing.",
        },
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200
    assert response.json()["updated_by_id"] == school_admin_user.id


# ----------------------------------------------------------------------
# Read endpoints
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_school_staff_can_list_and_filter_shared_content(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    report_session = await _create_report_session(
        db_session,
        school_id=teacher_user.school_id,
    )

    class_group = await _create_class_group(
        db_session,
        school_id=teacher_user.school_id,
        teacher_id=teacher_user.id,
    )

    await _create_shared_content(
        db_session,
        school_id=teacher_user.school_id,
        report_session_id=report_session.id,
        class_group_id=class_group.id,
        subject_name="Chemistry",
        updated_by_id=teacher_user.id,
    )

    await _create_shared_content(
        db_session,
        school_id=teacher_user.school_id,
        report_session_id=report_session.id,
        class_group_id=class_group.id,
        subject_name="Physics",
        work_covered="Forces, motion and energy.",
        updated_by_id=teacher_user.id,
    )

    response = await client.get(
        f"{BASE_URL}/",
        params={
            "report_session_id": report_session.id,
            "class_group_id": class_group.id,
            "subject_name": "Physics",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 1
    assert body[0]["subject_name"] == "Physics"
    assert body[0]["work_covered"] == "Forces, motion and energy."


@pytest.mark.asyncio
async def test_school_staff_can_get_shared_content_by_scope(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    report_session = await _create_report_session(
        db_session,
        school_id=teacher_user.school_id,
    )

    class_group = await _create_class_group(
        db_session,
        school_id=teacher_user.school_id,
        teacher_id=teacher_user.id,
    )

    record = await _create_shared_content(
        db_session,
        school_id=teacher_user.school_id,
        report_session_id=report_session.id,
        class_group_id=class_group.id,
        subject_name="Biology",
        work_covered="Cells, microscopy and transport.",
        updated_by_id=teacher_user.id,
    )

    response = await client.get(
        f"{BASE_URL}/scope",
        params={
            "report_session_id": report_session.id,
            "class_group_id": class_group.id,
            "subject_name": "Biology",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == record.id
    assert body["subject_name"] == "Biology"
    assert body["work_covered"] == "Cells, microscopy and transport."


@pytest.mark.asyncio
async def test_scope_lookup_returns_404_when_content_does_not_exist(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    report_session = await _create_report_session(
        db_session,
        school_id=teacher_user.school_id,
    )

    class_group = await _create_class_group(
        db_session,
        school_id=teacher_user.school_id,
        teacher_id=teacher_user.id,
    )

    response = await client.get(
        f"{BASE_URL}/scope",
        params={
            "report_session_id": report_session.id,
            "class_group_id": class_group.id,
            "subject_name": "Art",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 404
    assert _error_message(response) == "Shared report content not found."


@pytest.mark.asyncio
async def test_school_staff_can_get_shared_content_by_id(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    report_session = await _create_report_session(
        db_session,
        school_id=teacher_user.school_id,
    )

    class_group = await _create_class_group(
        db_session,
        school_id=teacher_user.school_id,
        teacher_id=teacher_user.id,
    )

    record = await _create_shared_content(
        db_session,
        school_id=teacher_user.school_id,
        report_session_id=report_session.id,
        class_group_id=class_group.id,
        subject_name="Geography",
        work_covered="Rivers and coastal processes.",
        updated_by_id=teacher_user.id,
    )

    response = await client.get(
        f"{BASE_URL}/{record.id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200
    assert response.json()["id"] == record.id
    assert response.json()["subject_name"] == "Geography"


@pytest.mark.asyncio
async def test_get_by_id_returns_404_for_unknown_content(
    client: AsyncClient,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        f"{BASE_URL}/999999",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 404
    assert _error_message(response) == "Shared report content not found."


# ----------------------------------------------------------------------
# Update endpoint
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assigned_teacher_can_update_shared_content(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    report_session = await _create_report_session(
        db_session,
        school_id=teacher_user.school_id,
    )

    class_group = await _create_class_group(
        db_session,
        school_id=teacher_user.school_id,
        teacher_id=teacher_user.id,
    )

    record = await _create_shared_content(
        db_session,
        school_id=teacher_user.school_id,
        report_session_id=report_session.id,
        class_group_id=class_group.id,
        subject_name="Chemistry",
        updated_by_id=teacher_user.id,
    )

    response = await client.patch(
        f"{BASE_URL}/{record.id}",
        json={
            "work_covered": (
                "  Acids, alkalis, neutralisation and preparation of salts.  "
            ),
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == record.id
    assert body["work_covered"] == (
        "Acids, alkalis, neutralisation and preparation of salts."
    )
    assert body["updated_by_id"] == teacher_user.id


@pytest.mark.asyncio
async def test_teacher_cannot_update_unassigned_class_content(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    school_admin_user,
    auth_headers,
):
    report_session = await _create_report_session(
        db_session,
        school_id=teacher_user.school_id,
    )

    class_group = await _create_class_group(
        db_session,
        school_id=teacher_user.school_id,
        teacher_id=school_admin_user.id,
    )

    record = await _create_shared_content(
        db_session,
        school_id=teacher_user.school_id,
        report_session_id=report_session.id,
        class_group_id=class_group.id,
        updated_by_id=school_admin_user.id,
    )

    response = await client.patch(
        f"{BASE_URL}/{record.id}",
        json={
            "work_covered": "Attempted unauthorised update.",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 403


# ----------------------------------------------------------------------
# Delete endpoint
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teacher_cannot_delete_shared_content(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    report_session = await _create_report_session(
        db_session,
        school_id=teacher_user.school_id,
    )

    class_group = await _create_class_group(
        db_session,
        school_id=teacher_user.school_id,
        teacher_id=teacher_user.id,
    )

    record = await _create_shared_content(
        db_session,
        school_id=teacher_user.school_id,
        report_session_id=report_session.id,
        class_group_id=class_group.id,
        updated_by_id=teacher_user.id,
    )

    response = await client.delete(
        f"{BASE_URL}/{record.id}",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 403

    await db_session.refresh(record)
    assert record.id is not None


@pytest.mark.asyncio
async def test_school_admin_can_delete_shared_content(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    teacher_user,
    auth_headers,
):
    report_session = await _create_report_session(
        db_session,
        school_id=school_admin_user.school_id,
    )

    class_group = await _create_class_group(
        db_session,
        school_id=school_admin_user.school_id,
        teacher_id=teacher_user.id,
    )

    record = await _create_shared_content(
        db_session,
        school_id=school_admin_user.school_id,
        report_session_id=report_session.id,
        class_group_id=class_group.id,
        updated_by_id=teacher_user.id,
    )

    record_id = record.id

    response = await client.delete(
        f"{BASE_URL}/{record_id}",
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 204
    assert response.content == b""

    result = await db_session.execute(
        select(ReportGroupContent).where(
            ReportGroupContent.id == record_id,
        )
    )

    assert result.scalar_one_or_none() is None


# ----------------------------------------------------------------------
# Scope and payload validation
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_rejects_unknown_report_session(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    class_group = await _create_class_group(
        db_session,
        school_id=teacher_user.school_id,
        teacher_id=teacher_user.id,
    )

    response = await client.put(
        f"{BASE_URL}/",
        json={
            "report_session_id": 999999,
            "class_group_id": class_group.id,
            "subject_name": "Physics",
            "work_covered": "Forces.",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 400
    assert _error_message(response) == (
        "The reporting session was not found for this school."
    )


@pytest.mark.asyncio
async def test_upsert_rejects_unknown_class_group(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    report_session = await _create_report_session(
        db_session,
        school_id=teacher_user.school_id,
    )

    response = await client.put(
        f"{BASE_URL}/",
        json={
            "report_session_id": report_session.id,
            "class_group_id": 999999,
            "subject_name": "Physics",
            "work_covered": "Forces.",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 400
    assert _error_message(response) == (
        "The class group was not found for this school."
    )


@pytest.mark.asyncio
async def test_upsert_rejects_blank_subject_name(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
):
    report_session = await _create_report_session(
        db_session,
        school_id=teacher_user.school_id,
    )

    class_group = await _create_class_group(
        db_session,
        school_id=teacher_user.school_id,
        teacher_id=teacher_user.id,
    )

    response = await client.put(
        f"{BASE_URL}/",
        json={
            "report_session_id": report_session.id,
            "class_group_id": class_group.id,
            "subject_name": "   ",
            "work_covered": "Forces.",
        },
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 422