from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User


async def log_audit_event(
    db: AsyncSession,
    *,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    target_user: User | None = None,
    target_user_id: int | None = None,
    school_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    resolved_target_user_id = (
        target_user.id if target_user is not None else target_user_id
    )

    audit_log = AuditLog(
        actor_id=actor.id if actor else None,
        actor_school_id=actor.school_id if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        target_user_id=resolved_target_user_id,
        school_id=(
            school_id if school_id is not None else actor.school_id if actor else None
        ),
        metadata_json=metadata or {},
    )

    db.add(audit_log)
    await db.flush()

    return audit_log


class AuditLogService:
    @staticmethod
    async def log(
        db: AsyncSession,
        *,
        actor: User | None,
        action: str,
        entity_type: str,
        entity_id: int | None = None,
        target_user: User | None = None,
        target_user_id: int | None = None,
        school_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        return await log_audit_event(
            db,
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            target_user=target_user,
            target_user_id=target_user_id,
            school_id=school_id,
            metadata=metadata,
        )
