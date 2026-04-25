from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogFilter


class AuditLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(
        self,
        filters: AuditLogFilter,
    ) -> list[AuditLog]:
        query = select(AuditLog).order_by(AuditLog.created_at.desc())

        # =========================
        # Filtering
        # =========================

        if filters.actor_id is not None:
            query = query.where(AuditLog.actor_id == filters.actor_id)

        if filters.target_user_id is not None:
            query = query.where(AuditLog.target_user_id == filters.target_user_id)

        if filters.school_id is not None:
            query = query.where(AuditLog.school_id == filters.school_id)

        if filters.action is not None:
            query = query.where(AuditLog.action == filters.action)

        if filters.entity_type is not None:
            query = query.where(AuditLog.entity_type == filters.entity_type)

        if filters.date_from is not None:
            query = query.where(AuditLog.created_at >= filters.date_from)

        if filters.date_to is not None:
            query = query.where(AuditLog.created_at <= filters.date_to)

        # =========================
        # Pagination
        # =========================

        query = query.offset(filters.offset).limit(filters.limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, log_id: int) -> Optional[AuditLog]:
        result = await self.db.execute(select(AuditLog).where(AuditLog.id == log_id))
        return result.scalar_one_or_none()
