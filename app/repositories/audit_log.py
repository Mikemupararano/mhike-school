from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_log import AuditLogFilter


class AuditLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _apply_filters(self, query, filters: AuditLogFilter):
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

        return query

    async def list(
        self,
        filters: AuditLogFilter,
    ) -> list[AuditLog]:
        ActorUser = aliased(User)
        TargetUser = aliased(User)

        query = (
            select(AuditLog)
            .outerjoin(ActorUser, AuditLog.actor_id == ActorUser.id)
            .outerjoin(TargetUser, AuditLog.target_user_id == TargetUser.id)
            .order_by(AuditLog.created_at.desc())
        )

        query = self._apply_filters(query, filters)

        if filters.actor_email:
            query = query.where(ActorUser.email.ilike(f"%{filters.actor_email}%"))

        if filters.target_user_email:
            query = query.where(
                TargetUser.email.ilike(f"%{filters.target_user_email}%")
            )

        query = query.offset(filters.offset).limit(filters.limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        filters: AuditLogFilter,
    ) -> int:
        ActorUser = aliased(User)
        TargetUser = aliased(User)

        query = (
            select(func.count(AuditLog.id))
            .select_from(AuditLog)
            .outerjoin(ActorUser, AuditLog.actor_id == ActorUser.id)
            .outerjoin(TargetUser, AuditLog.target_user_id == TargetUser.id)
        )

        query = self._apply_filters(query, filters)

        if filters.actor_email:
            query = query.where(ActorUser.email.ilike(f"%{filters.actor_email}%"))

        if filters.target_user_email:
            query = query.where(
                TargetUser.email.ilike(f"%{filters.target_user_email}%")
            )

        result = await self.db.execute(query)
        return int(result.scalar_one() or 0)

    async def get_by_id(self, log_id: int) -> Optional[AuditLog]:
        result = await self.db.execute(select(AuditLog).where(AuditLog.id == log_id))
        return result.scalar_one_or_none()
