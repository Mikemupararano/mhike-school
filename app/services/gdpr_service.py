from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserStatus
from app.services.audit_log_service import AuditLogService


class GDPRService:
    """
    Handles GDPR data lifecycle:
    - retention expiry
    - anonymisation
    """

    @staticmethod
    async def anonymise_expired_users(db: AsyncSession) -> int:
        """
        Find users whose retention has expired and anonymise them.

        Returns:
            int: number of users anonymised
        """

        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(User).where(
                User.retention_expires_at.is_not(None),
                User.retention_expires_at <= now,
                User.status.in_(
                    [
                        UserStatus.DEACTIVATED,
                        UserStatus.PENDING_ERASURE,
                    ]
                ),
            )
        )

        users = result.scalars().all()

        anonymised_count = 0

        for user in users:
            await GDPRService._anonymise_user(db, user)
            anonymised_count += 1

        return anonymised_count

    @staticmethod
    async def _anonymise_user(db: AsyncSession, user: User) -> None:
        """
        Internal anonymisation logic.
        MUST be irreversible.
        """

        original_email = user.email
        original_name = user.full_name

        user.full_name = f"Deleted User {user.id}"
        user.email = f"deleted-{user.id}@redacted.local"
        user.hashed_password = None

        user.status = UserStatus.ANONYMISED
        user.is_active = False
        user.anonymised_at = datetime.now(timezone.utc)

        # Clear retention data (optional but cleaner)
        user.retention_expires_at = None

        # =========================
        # Audit log
        # =========================
        await AuditLogService.log(
            db,
            actor=None,  # system action
            action="user_auto_anonymised",
            entity_type="user",
            entity_id=user.id,
            target_user=user,
            school_id=user.school_id,
            metadata={
                "previous_email": original_email,
                "previous_name": original_name,
                "reason": "retention_expired",
                "anonymised_at": user.anonymised_at.isoformat(),
            },
        )
