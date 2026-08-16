from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.services.assessment_notification_service as service
from app.models.assessment_result_outcome import (
    AssessmentResultChangeType,
)


class _FakeNotification:
    def __init__(
        self,
        *,
        user_id: int,
        title: str,
        message: str,
        priority: str,
    ) -> None:
        self.user_id = user_id
        self.title = title
        self.message = message
        self.priority = priority


class _FakeNotificationService:
    def __init__(
        self,
    ) -> None:
        self.calls: list[dict] = []

    async def create_notification(
        self,
        *,
        school_id,
        user_id,
        title,
        message,
        category,
        priority,
        email_enabled,
        push_enabled,
        sms_enabled,
    ):
        self.calls.append(
            {
                "school_id": school_id,
                "user_id": user_id,
                "title": title,
                "message": message,
                "category": category,
                "priority": priority,
                "email_enabled": email_enabled,
                "push_enabled": push_enabled,
                "sms_enabled": sms_enabled,
            }
        )

        return _FakeNotification(
            user_id=user_id,
            title=title,
            message=message,
            priority=priority,
        )


class _FakeParentStudentRepository:
    def __init__(
        self,
    ) -> None:
        self.parents_by_student: dict[int, list[int]] = {}
        self.calls: list[dict] = []

    async def list_parents_for_student(
        self,
        student_id,
        *,
        school_id,
        include_relationships,
    ):
        self.calls.append(
            {
                "student_id": student_id,
                "school_id": school_id,
                "include_relationships": include_relationships,
            }
        )

        return [
            SimpleNamespace(
                parent_id=parent_id,
            )
            for parent_id in self.parents_by_student.get(
                student_id,
                [],
            )
        ]


def _build_service():
    instance = object.__new__(
        service.AssessmentNotificationService,
    )

    instance.db = object()
    instance.notification_service = _FakeNotificationService()
    instance.parent_student_repository = _FakeParentStudentRepository()

    return instance


async def _allow_school_users(
    instance,
    *,
    allowed_user_ids: set[int],
):
    async def fake_require_user_in_school(
        *,
        user_id,
        school_id,
    ):
        if user_id not in allowed_user_ids:
            raise ValueError(
                (f"User {user_id} does not belong to " f"school {school_id}.")
            )

        return SimpleNamespace(
            id=user_id,
            school_id=school_id,
        )

    instance._require_user_in_school = fake_require_user_in_school


# ---------------------------------------------------------------------------
# Validation and normalisation
# ---------------------------------------------------------------------------


def test_normalise_user_ids_deduplicates_and_orders():
    result = service.AssessmentNotificationService._normalise_user_ids(
        [
            5,
            3,
            5,
            2,
            3,
        ]
    )

    assert result == [
        2,
        3,
        5,
    ]


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        True,
        False,
        "1",
        None,
    ],
)
def test_normalise_user_ids_rejects_invalid_ids(
    value,
):
    with pytest.raises(
        ValueError,
        match="user_id must be a positive integer",
    ):
        service.AssessmentNotificationService._normalise_user_ids(
            [
                value,
            ]
        )


def test_clean_required_text_trims_text():
    result = service.AssessmentNotificationService._clean_required_text(
        "  Physics Test  ",
        "assessment_title",
    )

    assert result == "Physics Test"


def test_clean_required_text_rejects_blank():
    with pytest.raises(
        ValueError,
        match="assessment_title cannot be blank",
    ):
        service.AssessmentNotificationService._clean_required_text(
            "   ",
            "assessment_title",
        )


# ---------------------------------------------------------------------------
# Core notification helper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notify_user_creates_assessment_notification():
    instance = _build_service()

    await _allow_school_users(
        instance,
        allowed_user_ids={
            10,
        },
    )

    notification = await instance._notify_user(
        school_id=1,
        user_id=10,
        title="Assessment marking required",
        message="Physics Test has work ready for marking.",
    )

    assert notification.user_id == 10

    assert (
        len(
            instance.notification_service.calls,
        )
        == 1
    )

    call = instance.notification_service.calls[0]

    assert call["school_id"] == 1
    assert call["user_id"] == 10
    assert call["category"] == "assessment"
    assert call["priority"] == "normal"

    assert call["email_enabled"] is False
    assert call["push_enabled"] is False
    assert call["sms_enabled"] is False


@pytest.mark.asyncio
async def test_notify_user_rejects_cross_school_recipient():
    instance = _build_service()

    await _allow_school_users(
        instance,
        allowed_user_ids=set(),
    )

    with pytest.raises(
        ValueError,
        match="does not belong to school",
    ):
        await instance._notify_user(
            school_id=1,
            user_id=999,
            title="Assessment marking required",
            message="Physics Test has work ready for marking.",
        )

    assert instance.notification_service.calls == []


@pytest.mark.asyncio
async def test_notify_users_deduplicates_recipients():
    instance = _build_service()

    await _allow_school_users(
        instance,
        allowed_user_ids={
            10,
            20,
        },
    )

    notifications = await instance._notify_users(
        school_id=1,
        user_ids=[
            20,
            10,
            20,
            10,
        ],
        title="Assessment notification",
        message="Something happened.",
    )

    assert [notification.user_id for notification in notifications] == [
        10,
        20,
    ]

    assert [call["user_id"] for call in instance.notification_service.calls] == [
        10,
        20,
    ]


# ---------------------------------------------------------------------------
# Results published
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_results_published_notifies_students_and_parents():
    instance = _build_service()

    instance.parent_student_repository.parents_by_student = {
        101: [
            201,
            202,
        ],
        102: [
            202,
            203,
        ],
    }

    await _allow_school_users(
        instance,
        allowed_user_ids={
            101,
            102,
            201,
            202,
            203,
        },
    )

    notifications = await instance.notify_results_published(
        assessment_id=50,
        assessment_title="Physics Forces Test",
        school_id=1,
        student_ids=[
            101,
            102,
        ],
        include_parents=True,
    )

    assert [notification.user_id for notification in notifications] == [
        101,
        102,
        201,
        202,
        203,
    ]

    assert (
        len(
            instance.parent_student_repository.calls,
        )
        == 2
    )

    assert all(
        call["school_id"] == 1 for call in instance.parent_student_repository.calls
    )

    assert all(
        call["include_relationships"] is False
        for call in instance.parent_student_repository.calls
    )

    assert all(
        call["title"] == "Assessment results published"
        for call in instance.notification_service.calls
    )

    assert all(
        ("Official results for Physics Forces Test " "are now available.")
        == call["message"]
        for call in instance.notification_service.calls
    )


@pytest.mark.asyncio
async def test_results_published_can_exclude_parents():
    instance = _build_service()

    instance.parent_student_repository.parents_by_student = {
        101: [
            201,
        ],
    }

    await _allow_school_users(
        instance,
        allowed_user_ids={
            101,
        },
    )

    notifications = await instance.notify_results_published(
        assessment_id=50,
        assessment_title="Physics Forces Test",
        school_id=1,
        student_ids=[
            101,
        ],
        include_parents=False,
    )

    assert [notification.user_id for notification in notifications] == [
        101,
    ]

    assert instance.parent_student_repository.calls == []


@pytest.mark.asyncio
async def test_results_published_deduplicates_shared_parent():
    instance = _build_service()

    instance.parent_student_repository.parents_by_student = {
        101: [
            201,
        ],
        102: [
            201,
        ],
    }

    await _allow_school_users(
        instance,
        allowed_user_ids={
            101,
            102,
            201,
        },
    )

    notifications = await instance.notify_results_published(
        assessment_id=50,
        assessment_title="Physics Forces Test",
        school_id=1,
        student_ids=[
            101,
            102,
        ],
    )

    assert [notification.user_id for notification in notifications] == [
        101,
        102,
        201,
    ]


@pytest.mark.asyncio
async def test_results_published_student_only_audience():
    instance = _build_service()

    instance.parent_student_repository.parents_by_student = {
        101: [
            201,
        ],
    }

    await _allow_school_users(
        instance,
        allowed_user_ids={
            101,
        },
    )

    notifications = await instance.notify_results_published(
        assessment_id=50,
        assessment_title="Physics Forces Test",
        school_id=1,
        student_ids=[
            101,
        ],
        notify_students=True,
        notify_parents=False,
    )

    assert [notification.user_id for notification in notifications] == [
        101,
    ]

    assert instance.parent_student_repository.calls == []


@pytest.mark.asyncio
async def test_results_published_parent_only_audience():
    instance = _build_service()

    instance.parent_student_repository.parents_by_student = {
        101: [
            201,
            202,
        ],
    }

    await _allow_school_users(
        instance,
        allowed_user_ids={
            201,
            202,
        },
    )

    notifications = await instance.notify_results_published(
        assessment_id=50,
        assessment_title="Physics Forces Test",
        school_id=1,
        student_ids=[
            101,
        ],
        notify_students=False,
        notify_parents=True,
    )

    assert [notification.user_id for notification in notifications] == [
        201,
        202,
    ]

    assert (
        len(
            instance.parent_student_repository.calls,
        )
        == 1
    )


@pytest.mark.asyncio
async def test_results_published_both_audiences():
    instance = _build_service()

    instance.parent_student_repository.parents_by_student = {
        101: [
            201,
        ],
    }

    await _allow_school_users(
        instance,
        allowed_user_ids={
            101,
            201,
        },
    )

    notifications = await instance.notify_results_published(
        assessment_id=50,
        assessment_title="Physics Forces Test",
        school_id=1,
        student_ids=[
            101,
        ],
        notify_students=True,
        notify_parents=True,
    )

    assert [notification.user_id for notification in notifications] == [
        101,
        201,
    ]


@pytest.mark.asyncio
async def test_results_published_no_audience_returns_empty():
    instance = _build_service()

    instance.parent_student_repository.parents_by_student = {
        101: [
            201,
        ],
    }

    await _allow_school_users(
        instance,
        allowed_user_ids=set(),
    )

    notifications = await instance.notify_results_published(
        assessment_id=50,
        assessment_title="Physics Forces Test",
        school_id=1,
        student_ids=[
            101,
        ],
        notify_students=False,
        notify_parents=False,
    )

    assert notifications == []
    assert instance.parent_student_repository.calls == []
    assert instance.notification_service.calls == []


@pytest.mark.asyncio
async def test_results_published_legacy_include_parents_overrides_new_parent_flag():
    instance = _build_service()

    instance.parent_student_repository.parents_by_student = {
        101: [
            201,
        ],
    }

    await _allow_school_users(
        instance,
        allowed_user_ids={
            101,
        },
    )

    notifications = await instance.notify_results_published(
        assessment_id=50,
        assessment_title="Physics Forces Test",
        school_id=1,
        student_ids=[
            101,
        ],
        notify_students=True,
        notify_parents=True,
        include_parents=False,
    )

    assert [notification.user_id for notification in notifications] == [
        101,
    ]

    assert instance.parent_student_repository.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "field_name",
        "kwargs",
    ),
    [
        (
            "notify_students",
            {
                "notify_students": 1,
            },
        ),
        (
            "notify_parents",
            {
                "notify_parents": 1,
            },
        ),
        (
            "include_parents",
            {
                "include_parents": 1,
            },
        ),
    ],
)
async def test_results_published_rejects_invalid_audience_flags(
    field_name,
    kwargs,
):
    instance = _build_service()

    with pytest.raises(
        ValueError,
        match=field_name,
    ):
        await instance.notify_results_published(
            assessment_id=50,
            assessment_title="Physics Forces Test",
            school_id=1,
            student_ids=[
                101,
            ],
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Marking required
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_marking_required_notifies_marker():
    instance = _build_service()

    await _allow_school_users(
        instance,
        allowed_user_ids={
            301,
        },
    )

    notification = await instance.notify_marking_required(
        assessment_id=50,
        assessment_title="Physics Forces Test",
        school_id=1,
        marker_user_id=301,
    )

    assert notification.user_id == 301
    assert notification.title == "Assessment marking required"

    assert notification.message == ("Physics Forces Test has work ready for marking.")


# ---------------------------------------------------------------------------
# Moderation required
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_moderation_required_notifies_moderator():
    instance = _build_service()

    await _allow_school_users(
        instance,
        allowed_user_ids={
            401,
        },
    )

    notification = await instance.notify_moderation_required(
        assessment_id=50,
        assessment_title="Physics Forces Test",
        school_id=1,
        moderator_user_id=401,
    )

    assert notification.user_id == 401
    assert notification.title == "Assessment moderation required"

    assert notification.message == (
        "Physics Forces Test is ready for moderation review."
    )


# ---------------------------------------------------------------------------
# Result-change labels
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    (
        "change_type",
        "expected",
    ),
    [
        (
            AssessmentResultChangeType.INITIAL,
            "initial result",
        ),
        (
            AssessmentResultChangeType.RETAKE,
            "retake",
        ),
        (
            AssessmentResultChangeType.REMARK,
            "remark",
        ),
        (
            AssessmentResultChangeType.CORRECTION,
            "correction",
        ),
        (
            AssessmentResultChangeType.MODERATION,
            "moderation",
        ),
        (
            AssessmentResultChangeType.ADMINISTRATIVE,
            "administrative update",
        ),
    ],
)
def test_result_change_label(
    change_type,
    expected,
):
    assert (
        service.AssessmentNotificationService._result_change_label(
            change_type,
        )
        == expected
    )


def test_result_change_label_rejects_unknown_value():
    with pytest.raises(
        ValueError,
        match="Unsupported assessment result change type",
    ):
        service.AssessmentNotificationService._result_change_label(
            object(),
        )


# ---------------------------------------------------------------------------
# Official result changed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_official_result_changed_notifies_student_and_parents():
    instance = _build_service()

    instance.parent_student_repository.parents_by_student = {
        101: [
            201,
            202,
        ],
    }

    await _allow_school_users(
        instance,
        allowed_user_ids={
            101,
            201,
            202,
        },
    )

    notifications = await instance.notify_official_result_changed(
        assessment_id=50,
        assessment_title="Physics Forces Test",
        school_id=1,
        student_id=101,
        change_type=AssessmentResultChangeType.REMARK,
        notify_student=True,
        notify_parents=True,
    )

    assert [notification.user_id for notification in notifications] == [
        101,
        201,
        202,
    ]

    assert all(
        notification.title == "Official assessment result updated"
        for notification in notifications
    )

    assert all(
        notification.message
        == (
            "Official result for Physics Forces Test "
            "has been updated following a remark."
        )
        for notification in notifications
    )

    assert all(notification.priority == "high" for notification in notifications)


@pytest.mark.asyncio
async def test_official_result_changed_student_only_audience():
    instance = _build_service()

    instance.parent_student_repository.parents_by_student = {
        101: [
            201,
        ],
    }

    await _allow_school_users(
        instance,
        allowed_user_ids={
            101,
        },
    )

    notifications = await instance.notify_official_result_changed(
        assessment_id=50,
        assessment_title="Physics Forces Test",
        school_id=1,
        student_id=101,
        change_type=AssessmentResultChangeType.CORRECTION,
        notify_student=True,
        notify_parents=False,
    )

    assert [notification.user_id for notification in notifications] == [
        101,
    ]

    assert instance.parent_student_repository.calls == []


@pytest.mark.asyncio
async def test_official_result_changed_parent_only_audience():
    instance = _build_service()

    instance.parent_student_repository.parents_by_student = {
        101: [
            201,
            202,
        ],
    }

    await _allow_school_users(
        instance,
        allowed_user_ids={
            201,
            202,
        },
    )

    notifications = await instance.notify_official_result_changed(
        assessment_id=50,
        assessment_title="Physics Forces Test",
        school_id=1,
        student_id=101,
        change_type=AssessmentResultChangeType.MODERATION,
        notify_student=False,
        notify_parents=True,
    )

    assert [notification.user_id for notification in notifications] == [
        201,
        202,
    ]

    assert (
        len(
            instance.parent_student_repository.calls,
        )
        == 1
    )


@pytest.mark.asyncio
async def test_official_result_changed_no_audience_returns_empty():
    instance = _build_service()

    instance.parent_student_repository.parents_by_student = {
        101: [
            201,
        ],
    }

    await _allow_school_users(
        instance,
        allowed_user_ids=set(),
    )

    notifications = await instance.notify_official_result_changed(
        assessment_id=50,
        assessment_title="Physics Forces Test",
        school_id=1,
        student_id=101,
        change_type=AssessmentResultChangeType.ADMINISTRATIVE,
        notify_student=False,
        notify_parents=False,
    )

    assert notifications == []
    assert instance.parent_student_repository.calls == []
    assert instance.notification_service.calls == []


@pytest.mark.asyncio
async def test_official_result_changed_legacy_include_parents_overrides_new_flag():
    instance = _build_service()

    instance.parent_student_repository.parents_by_student = {
        101: [
            201,
        ],
    }

    await _allow_school_users(
        instance,
        allowed_user_ids={
            101,
        },
    )

    notifications = await instance.notify_official_result_changed(
        assessment_id=50,
        assessment_title="Physics Forces Test",
        school_id=1,
        student_id=101,
        change_type=AssessmentResultChangeType.CORRECTION,
        notify_student=True,
        notify_parents=True,
        include_parents=False,
    )

    assert [notification.user_id for notification in notifications] == [
        101,
    ]

    assert instance.parent_student_repository.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "field_name",
        "kwargs",
    ),
    [
        (
            "notify_student",
            {
                "notify_student": 1,
            },
        ),
        (
            "notify_parents",
            {
                "notify_parents": 1,
            },
        ),
        (
            "include_parents",
            {
                "include_parents": 1,
            },
        ),
    ],
)
async def test_official_result_changed_rejects_invalid_audience_flags(
    field_name,
    kwargs,
):
    instance = _build_service()

    with pytest.raises(
        ValueError,
        match=field_name,
    ):
        await instance.notify_official_result_changed(
            assessment_id=50,
            assessment_title="Physics Forces Test",
            school_id=1,
            student_id=101,
            change_type=AssessmentResultChangeType.REMARK,
            **kwargs,
        )


@pytest.mark.asyncio
async def test_official_result_changed_uses_change_type_wording():
    instance = _build_service()

    await _allow_school_users(
        instance,
        allowed_user_ids={
            101,
        },
    )

    notifications = await instance.notify_official_result_changed(
        assessment_id=50,
        assessment_title="Physics Forces Test",
        school_id=1,
        student_id=101,
        change_type=AssessmentResultChangeType.RETAKE,
        notify_student=True,
        notify_parents=False,
    )

    assert notifications[0].message == (
        "Official result for Physics Forces Test "
        "has been updated following a retake."
    )


# ---------------------------------------------------------------------------
# External-delivery safety
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assessment_notifications_do_not_enable_external_channels():
    instance = _build_service()

    await _allow_school_users(
        instance,
        allowed_user_ids={
            301,
        },
    )

    await instance.notify_marking_required(
        assessment_id=50,
        assessment_title="Physics Forces Test",
        school_id=1,
        marker_user_id=301,
    )

    assert (
        len(
            instance.notification_service.calls,
        )
        == 1
    )

    call = instance.notification_service.calls[0]

    assert call["email_enabled"] is False
    assert call["push_enabled"] is False
    assert call["sms_enabled"] is False
