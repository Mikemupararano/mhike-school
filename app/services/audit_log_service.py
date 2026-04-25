from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User


class AuditLogService:
    """
    Centralised audit logging service.

    IMPORTANT:
    - Always call this from SERVICES (not endpoints)
    - Never fail the main operation if logging fails
    """

    @staticmethod
    async def log(
        db: AsyncSession,
        *,
        actor: Optional[User],
        action: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        target_user: Optional[User] = None,
        school_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        commit: bool = False,
    ) -> None:
        """
        Generic audit log entry.
        """

        try:
            log_entry = AuditLog(
                actor_id=actor.id if actor else None,
                actor_school_id=actor.school_id if actor else None,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                target_user_id=target_user.id if target_user else None,
                school_id=(
                    school_id
                    if school_id is not None
                    else (actor.school_id if actor else None)
                ),
                metadata_json=metadata,
            )

            db.add(log_entry)

            # Usually we DON'T commit here
            # Let the parent transaction handle it
            if commit:
                await db.commit()

        except Exception:
            # CRITICAL DESIGN:
            # Audit logging must NEVER break business logic
            pass

    # =========================
    # Convenience methods
    # =========================

    @staticmethod
    async def log_user_created(
        db: AsyncSession,
        *,
        actor: Optional[User],
        target_user: User,
    ) -> None:
        await AuditLogService.log(
            db,
            actor=actor,
            action="user_created",
            entity_type="user",
            entity_id=target_user.id,
            target_user=target_user,
            school_id=target_user.school_id,
        )

    @staticmethod
    async def log_user_updated(
        db: AsyncSession,
        *,
        actor: Optional[User],
        target_user: User,
        changes: Dict[str, Any],
    ) -> None:
        await AuditLogService.log(
            db,
            actor=actor,
            action="user_updated",
            entity_type="user",
            entity_id=target_user.id,
            target_user=target_user,
            school_id=target_user.school_id,
            metadata={"changes": changes},
        )

    @staticmethod
    async def log_user_deleted(
        db: AsyncSession,
        *,
        actor: Optional[User],
        target_user: User,
    ) -> None:
        await AuditLogService.log(
            db,
            actor=actor,
            action="user_deleted",
            entity_type="user",
            entity_id=target_user.id,
            target_user=target_user,
            school_id=target_user.school_id,
        )

    @staticmethod
    async def log_role_changed(
        db: AsyncSession,
        *,
        actor: Optional[User],
        target_user: User,
        old_roles: list[str],
        new_roles: list[str],
    ) -> None:
        await AuditLogService.log(
            db,
            actor=actor,
            action="role_changed",
            entity_type="user",
            entity_id=target_user.id,
            target_user=target_user,
            school_id=target_user.school_id,
            metadata={
                "old_roles": old_roles,
                "new_roles": new_roles,
            },
        )

    @staticmethod
    async def log_user_anonymised(
        db: AsyncSession,
        *,
        actor: Optional[User],
        target_user: User,
    ) -> None:
        await AuditLogService.log(
            db,
            actor=actor,
            action="user_anonymised",
            entity_type="user",
            entity_id=target_user.id,
            target_user=target_user,
            school_id=target_user.school_id,
        )
