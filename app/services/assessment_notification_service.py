from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_result_outcome import (
    AssessmentResultChangeType,
)
from app.models.notification import Notification
from app.models.user import User
from app.repositories.parent_student import ParentStudentRepository
from app.services.notification_service import NotificationService

ASSESSMENT_NOTIFICATION_CATEGORY = "assessment"


class AssessmentNotificationService:
    """
    Orchestrate assessment-related notifications.

    This service deliberately reuses ``NotificationService`` rather than
    creating a parallel notification subsystem.

    Assessment notification responsibilities are limited to:

    * identifying recipients;
    * enforcing school scope;
    * producing assessment-specific titles/messages;
    * delegating persistence and realtime delivery to NotificationService.

    External email, push-provider and SMS delivery channels remain disabled
    here until the corresponding provider integrations are real. Persistent
    in-app notifications and realtime socket events still occur through
    NotificationService.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db
        self.notification_service = NotificationService(
            db,
        )
        self.parent_student_repository = ParentStudentRepository(
            db,
        )

    # ------------------------------------------------------------------
    # Validation / recipient helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_positive_integer(
        value: int,
        field_name: str,
    ) -> None:
        if (
            not isinstance(
                value,
                int,
            )
            or isinstance(
                value,
                bool,
            )
            or value < 1
        ):
            raise ValueError(
                f"{field_name} must be a positive integer.",
            )

    @staticmethod
    def _clean_required_text(
        value: str,
        field_name: str,
    ) -> str:
        cleaned = str(
            value,
        ).strip()

        if not cleaned:
            raise ValueError(
                f"{field_name} cannot be blank.",
            )

        return cleaned

    @staticmethod
    def _normalise_user_ids(
        user_ids: Iterable[int],
    ) -> list[int]:
        """
        Validate, deduplicate and deterministically order user IDs.
        """

        normalised: set[int] = set()

        for user_id in user_ids:
            AssessmentNotificationService._validate_positive_integer(
                user_id,
                "user_id",
            )

            normalised.add(
                user_id,
            )

        return sorted(
            normalised,
        )

    async def _get_user_in_school(
        self,
        *,
        user_id: int,
        school_id: int,
    ) -> User | None:
        self._validate_positive_integer(
            user_id,
            "user_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        result = await self.db.execute(
            select(
                User,
            ).where(
                User.id == user_id,
                User.school_id == school_id,
            ),
        )

        return result.scalar_one_or_none()

    async def _require_user_in_school(
        self,
        *,
        user_id: int,
        school_id: int,
    ) -> User:
        user = await self._get_user_in_school(
            user_id=user_id,
            school_id=school_id,
        )

        if user is None:
            raise ValueError(
                (f"User {user_id} does not belong to " f"school {school_id}."),
            )

        return user

    async def _get_parent_user_ids(
        self,
        *,
        student_id: int,
        school_id: int,
    ) -> list[int]:
        """
        Return school-scoped parent recipients for one student.
        """

        links = await self.parent_student_repository.list_parents_for_student(
            student_id,
            school_id=school_id,
            include_relationships=False,
        )

        return self._normalise_user_ids(link.parent_id for link in links)

    # ------------------------------------------------------------------
    # Core notification helper
    # ------------------------------------------------------------------

    async def _notify_user(
        self,
        *,
        school_id: int,
        user_id: int,
        title: str,
        message: str,
        priority: str = "normal",
    ) -> Notification:
        """
        Create one assessment notification for one school-scoped user.

        External provider channels are intentionally disabled until the
        production email/push/SMS implementations exist. NotificationService
        still persists the notification and emits its realtime socket event.
        """

        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        await self._require_user_in_school(
            user_id=user_id,
            school_id=school_id,
        )

        cleaned_title = self._clean_required_text(
            title,
            "title",
        )
        cleaned_message = self._clean_required_text(
            message,
            "message",
        )

        return await self.notification_service.create_notification(
            school_id=school_id,
            user_id=user_id,
            title=cleaned_title,
            message=cleaned_message,
            category=ASSESSMENT_NOTIFICATION_CATEGORY,
            priority=priority,
            email_enabled=False,
            push_enabled=False,
            sms_enabled=False,
        )

    async def _notify_users(
        self,
        *,
        school_id: int,
        user_ids: Iterable[int],
        title: str,
        message: str,
        priority: str = "normal",
    ) -> list[Notification]:
        """
        Create one notification per unique recipient.
        """

        recipient_ids = self._normalise_user_ids(
            user_ids,
        )

        notifications: list[Notification] = []

        for user_id in recipient_ids:
            notification = await self._notify_user(
                school_id=school_id,
                user_id=user_id,
                title=title,
                message=message,
                priority=priority,
            )

            notifications.append(
                notification,
            )

        return notifications

    # ------------------------------------------------------------------
    # Results published
    # ------------------------------------------------------------------

    async def notify_results_published(
        self,
        *,
        assessment_id: int,
        assessment_title: str,
        school_id: int,
        student_ids: Iterable[int],
        notify_students: bool = True,
        notify_parents: bool = True,
        include_parents: bool | None = None,
    ) -> list[Notification]:
        """
        Notify the configured student and/or parent audiences that official
        assessment results have been published.

        ``student_ids`` identifies the students whose authoritative results
        are part of the release. The IDs are still required for parent lookup
        when ``notify_students=False`` and ``notify_parents=True``.

        Recipient IDs are deduplicated so one parent linked to several
        included students receives only one notification for the assessment.

        ``include_parents`` is retained temporarily as a backwards-compatible
        alias for the former API. When supplied, it overrides
        ``notify_parents``. New callers should use ``notify_students`` and
        ``notify_parents`` explicitly so publication visibility can be mapped
        without ambiguity.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )

        if not isinstance(
            notify_students,
            bool,
        ):
            raise ValueError(
                "notify_students must be a boolean.",
            )

        if not isinstance(
            notify_parents,
            bool,
        ):
            raise ValueError(
                "notify_parents must be a boolean.",
            )

        if include_parents is not None:
            if not isinstance(
                include_parents,
                bool,
            ):
                raise ValueError(
                    "include_parents must be a boolean or null.",
                )

            notify_parents = include_parents

        cleaned_title = self._clean_required_text(
            assessment_title,
            "assessment_title",
        )

        students = self._normalise_user_ids(
            student_ids,
        )

        recipient_ids: set[int] = set()

        if notify_students:
            recipient_ids.update(
                students,
            )

        if notify_parents:
            for student_id in students:
                parent_ids = await self._get_parent_user_ids(
                    student_id=student_id,
                    school_id=school_id,
                )

                recipient_ids.update(
                    parent_ids,
                )

        if not recipient_ids:
            return []

        return await self._notify_users(
            school_id=school_id,
            user_ids=recipient_ids,
            title="Assessment results published",
            message=(f"Official results for {cleaned_title} " "are now available."),
            priority="normal",
        )

    # ------------------------------------------------------------------
    # Marking required
    # ------------------------------------------------------------------

    async def notify_marking_required(
        self,
        *,
        assessment_id: int,
        assessment_title: str,
        school_id: int,
        marker_user_id: int,
    ) -> Notification:
        """
        Notify the teacher or marker responsible for assessment marking.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        cleaned_title = self._clean_required_text(
            assessment_title,
            "assessment_title",
        )

        return await self._notify_user(
            school_id=school_id,
            user_id=marker_user_id,
            title="Assessment marking required",
            message=(f"{cleaned_title} has work ready for marking."),
            priority="normal",
        )

    # ------------------------------------------------------------------
    # Moderation required
    # ------------------------------------------------------------------

    async def notify_moderation_required(
        self,
        *,
        assessment_id: int,
        assessment_title: str,
        school_id: int,
        moderator_user_id: int,
    ) -> Notification:
        """
        Notify the assigned reviewer/moderator that moderation is required.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )

        cleaned_title = self._clean_required_text(
            assessment_title,
            "assessment_title",
        )

        return await self._notify_user(
            school_id=school_id,
            user_id=moderator_user_id,
            title="Assessment moderation required",
            message=(f"{cleaned_title} is ready for moderation review."),
            priority="normal",
        )

    # ------------------------------------------------------------------
    # Official result changed
    # ------------------------------------------------------------------

    @staticmethod
    def _result_change_label(
        change_type: AssessmentResultChangeType,
    ) -> str:
        labels = {
            AssessmentResultChangeType.INITIAL: "initial result",
            AssessmentResultChangeType.RETAKE: "retake",
            AssessmentResultChangeType.REMARK: "remark",
            AssessmentResultChangeType.CORRECTION: "correction",
            AssessmentResultChangeType.MODERATION: "moderation",
            AssessmentResultChangeType.ADMINISTRATIVE: ("administrative update"),
        }

        try:
            return labels[change_type]
        except KeyError as exc:
            raise ValueError(
                ("Unsupported assessment result change type: " f"{change_type!r}."),
            ) from exc

    async def notify_official_result_changed(
        self,
        *,
        assessment_id: int,
        assessment_title: str,
        school_id: int,
        student_id: int,
        change_type: AssessmentResultChangeType,
        include_parents: bool = True,
    ) -> list[Notification]:
        """
        Notify a student, and optionally linked parents, when the student's
        official authoritative result changes.

        This method must be called only after the new result has become
        authoritative. Draft or provisional result changes must not trigger
        this notification.
        """

        self._validate_positive_integer(
            assessment_id,
            "assessment_id",
        )
        self._validate_positive_integer(
            school_id,
            "school_id",
        )
        self._validate_positive_integer(
            student_id,
            "student_id",
        )

        cleaned_title = self._clean_required_text(
            assessment_title,
            "assessment_title",
        )

        change_label = self._result_change_label(
            change_type,
        )

        recipient_ids: set[int] = {
            student_id,
        }

        if include_parents:
            parent_ids = await self._get_parent_user_ids(
                student_id=student_id,
                school_id=school_id,
            )

            recipient_ids.update(
                parent_ids,
            )

        return await self._notify_users(
            school_id=school_id,
            user_ids=recipient_ids,
            title="Official assessment result updated",
            message=(
                f"Your official result for {cleaned_title} "
                f"has been updated following a {change_label}."
            ),
            priority="high",
        )
