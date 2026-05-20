import pytest

pytestmark = pytest.mark.asyncio


async def test_authenticated_user_can_get_notification_preferences(
    client,
    student_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/notification-preferences/me",
        headers=auth_headers(student_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["user_id"] == student_user.id
    assert data["attendance_alerts_enabled"] is True
    assert data["email_enabled"] is True


async def test_notification_preferences_requires_authentication(
    client,
):
    response = await client.get(
        "/api/v1/notification-preferences/me",
    )

    assert response.status_code in (401, 403)


async def test_user_can_update_notification_preferences(
    client,
    parent_user,
    auth_headers,
):
    payload = {
        "attendance_alerts_enabled": False,
        "absence_notifications_enabled": False,
        "persistent_absence_alerts_enabled": True,
        "safeguarding_alerts_enabled": True,
        "email_enabled": True,
        "push_enabled": True,
        "sms_enabled": False,
    }

    response = await client.patch(
        "/api/v1/notification-preferences/me",
        json=payload,
        headers=auth_headers(parent_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["attendance_alerts_enabled"] is False
    assert data["absence_notifications_enabled"] is False
    assert data["push_enabled"] is True


async def test_user_cannot_update_other_users_preferences(
    client,
    parent_user,
    student_user,
    auth_headers,
):
    payload = {
        "attendance_alerts_enabled": False,
    }

    response = await client.patch(
        f"/api/v1/notification-preferences/{student_user.id}",
        json=payload,
        headers=auth_headers(parent_user),
    )

    assert response.status_code in (403, 404, 405)


async def test_preferences_are_created_automatically(
    client,
    teacher_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/notification-preferences/me",
        headers=auth_headers(teacher_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["user_id"] == teacher_user.id
    assert data["school_id"] == teacher_user.school_id


async def test_platform_admin_without_school_cannot_create_preferences(
    client,
    platform_admin_user,
    auth_headers,
):
    response = await client.get(
        "/api/v1/notification-preferences/me",
        headers=auth_headers(platform_admin_user),
    )

    assert response.status_code in (400, 403)
