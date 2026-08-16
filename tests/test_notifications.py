import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.notification_service as notification_service_module
from app.models.notification import Notification
from app.models.notification_delivery import NotificationDelivery
from app.services.notification_service import NotificationService


@pytest.mark.asyncio
async def test_platform_admin_can_view_notification_metrics(
    client: AsyncClient,
    auth_headers,
    platform_admin_user,
):
    response = await client.get(
        "/api/v1/notifications/admin/metrics",
        headers=auth_headers(platform_admin_user),
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_school_admin_can_create_notification(
    client: AsyncClient,
    auth_headers,
    school_admin_user,
):
    payload = {
        "title": "Attendance Alert",
        "message": "Student attendance has dropped below threshold.",
        "category": "attendance",
        "priority": "high",
        "email_enabled": True,
        "push_enabled": True,
        "sms_enabled": False,
    }

    response = await client.post(
        "/api/v1/notifications",
        json=payload,
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["title"] == payload["title"]
    assert data["message"] == payload["message"]
    assert data["category"] == "attendance"
    assert data["priority"] == "high"
    assert data["email_enabled"] is True
    assert data["push_enabled"] is True


@pytest.mark.asyncio
async def test_student_cannot_create_notifications(
    client: AsyncClient,
    auth_headers,
    student_user,
):
    payload = {
        "title": "Unauthorised",
        "message": "Students should not create notifications.",
    }

    response = await client.post(
        "/api/v1/notifications",
        json=payload,
        headers=auth_headers(student_user),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_user_can_fetch_own_notifications(
    client: AsyncClient,
    db_session: AsyncSession,
    student_user,
    auth_headers,
):
    notification = Notification(
        school_id=student_user.school_id,
        user_id=student_user.id,
        title="Test Notification",
        message="This is a test notification.",
        category="general",
        priority="normal",
        email_enabled=False,
        push_enabled=True,
        sms_enabled=False,
        is_read=False,
    )

    db_session.add(notification)
    await db_session.commit()

    response = await client.get(
        "/api/v1/notifications/me",
        headers=auth_headers(student_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert any(item["title"] == "Test Notification" for item in data)


@pytest.mark.asyncio
async def test_user_can_mark_notification_as_read(
    client: AsyncClient,
    db_session: AsyncSession,
    student_user,
    auth_headers,
):
    notification = Notification(
        school_id=student_user.school_id,
        user_id=student_user.id,
        title="Unread Notification",
        message="Mark me as read.",
        category="general",
        priority="normal",
        email_enabled=False,
        push_enabled=True,
        sms_enabled=False,
        is_read=False,
    )

    db_session.add(notification)
    await db_session.commit()
    await db_session.refresh(notification)

    response = await client.patch(
        f"/api/v1/notifications/{notification.id}/read",
        headers=auth_headers(student_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["is_read"] is True
    assert data["read_at"] is not None


@pytest.mark.asyncio
async def test_notification_creation_creates_delivery_records(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers,
    school_admin_user,
):
    payload = {
        "title": "Delivery Test",
        "message": "Testing delivery creation.",
        "category": "system",
        "priority": "normal",
        "email_enabled": True,
        "push_enabled": True,
        "sms_enabled": True,
    }

    response = await client.post(
        "/api/v1/notifications",
        json=payload,
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 201

    notification_id = response.json()["id"]

    result = await db_session.execute(
        select(NotificationDelivery).where(
            NotificationDelivery.notification_id == notification_id,
        )
    )

    deliveries = list(result.scalars().all())

    assert len(deliveries) == 3

    channels = {delivery.channel for delivery in deliveries}

    assert channels == {"email", "push", "sms"}


# ---------------------------------------------------------------------------
# Realtime privacy routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_targeted_notification_emits_only_to_user_room(
    db_session: AsyncSession,
    student_user,
    monkeypatch,
):
    user_emissions: list[dict] = []
    school_emissions: list[dict] = []

    async def fake_emit_user_notification(
        *,
        user_id,
        payload,
    ):
        user_emissions.append(
            {
                "user_id": user_id,
                "payload": payload,
            }
        )

    async def fake_emit_school_notification(
        *,
        school_id,
        payload,
    ):
        school_emissions.append(
            {
                "school_id": school_id,
                "payload": payload,
            }
        )

    monkeypatch.setattr(
        notification_service_module,
        "emit_user_notification",
        fake_emit_user_notification,
    )
    monkeypatch.setattr(
        notification_service_module,
        "emit_school_notification",
        fake_emit_school_notification,
    )

    notification = await NotificationService(
        db_session,
    ).create_notification(
        school_id=student_user.school_id,
        user_id=student_user.id,
        title="Private assessment result",
        message="Your assessment result is available.",
        category="assessment",
        priority="high",
        email_enabled=False,
        push_enabled=False,
        sms_enabled=False,
    )

    assert notification.user_id == student_user.id
    assert notification.school_id == student_user.school_id

    assert len(user_emissions) == 1
    assert user_emissions[0]["user_id"] == student_user.id

    assert school_emissions == []


@pytest.mark.asyncio
async def test_school_wide_notification_emits_only_to_school_room(
    db_session: AsyncSession,
    school_admin_user,
    monkeypatch,
):
    user_emissions: list[dict] = []
    school_emissions: list[dict] = []

    async def fake_emit_user_notification(
        *,
        user_id,
        payload,
    ):
        user_emissions.append(
            {
                "user_id": user_id,
                "payload": payload,
            }
        )

    async def fake_emit_school_notification(
        *,
        school_id,
        payload,
    ):
        school_emissions.append(
            {
                "school_id": school_id,
                "payload": payload,
            }
        )

    monkeypatch.setattr(
        notification_service_module,
        "emit_user_notification",
        fake_emit_user_notification,
    )
    monkeypatch.setattr(
        notification_service_module,
        "emit_school_notification",
        fake_emit_school_notification,
    )

    notification = await NotificationService(
        db_session,
    ).create_notification(
        school_id=school_admin_user.school_id,
        user_id=None,
        title="School announcement",
        message="This message is intended for the school room.",
        category="general",
        priority="normal",
        email_enabled=False,
        push_enabled=False,
        sms_enabled=False,
    )

    assert notification.user_id is None
    assert notification.school_id == school_admin_user.school_id

    assert user_emissions == []

    assert len(school_emissions) == 1
    assert school_emissions[0]["school_id"] == school_admin_user.school_id


@pytest.mark.asyncio
async def test_user_targeted_notification_with_school_scope_never_emits_school_wide(
    db_session: AsyncSession,
    student_user,
    monkeypatch,
):
    user_emissions: list[dict] = []
    school_emissions: list[dict] = []

    async def fake_emit_user_notification(
        *,
        user_id,
        payload,
    ):
        user_emissions.append(
            {
                "user_id": user_id,
                "payload": payload,
            }
        )

    async def fake_emit_school_notification(
        *,
        school_id,
        payload,
    ):
        school_emissions.append(
            {
                "school_id": school_id,
                "payload": payload,
            }
        )

    monkeypatch.setattr(
        notification_service_module,
        "emit_user_notification",
        fake_emit_user_notification,
    )
    monkeypatch.setattr(
        notification_service_module,
        "emit_school_notification",
        fake_emit_school_notification,
    )

    await NotificationService(
        db_session,
    ).create_notification(
        school_id=student_user.school_id,
        user_id=student_user.id,
        title="Official assessment result updated",
        message="Official result has been updated following a remark.",
        category="assessment",
        priority="high",
        email_enabled=False,
        push_enabled=False,
        sms_enabled=False,
    )

    assert len(user_emissions) == 1
    assert user_emissions[0]["user_id"] == student_user.id
    assert school_emissions == []
