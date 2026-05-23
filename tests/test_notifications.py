import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.notification_delivery import NotificationDelivery


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
