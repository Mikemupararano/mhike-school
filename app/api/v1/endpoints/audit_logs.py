from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.user import User
from app.repositories.audit_log import AuditLogRepository
from app.schemas.audit_log import AuditLogFilter, AuditLogOut

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("/", response_model=list[AuditLogOut])
async def list_audit_logs(
    actor_id: int | None = Query(default=None),
    target_user_id: int | None = Query(default=None),
    school_id: int | None = Query(default=None),
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve audit logs.

    Access rules:
    - Platform admins → can view all logs
    - School admins → can only view logs for their school
    """

    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_platform_admin(current_user)

    # =========================
    # Enforce school isolation
    # =========================
    if not current_user.is_platform_admin:
        school_id = current_user.school_id

    filters = AuditLogFilter(
        actor_id=actor_id,
        target_user_id=target_user_id,
        school_id=school_id,
        action=action,
        entity_type=entity_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

    repo = AuditLogRepository(db)
    logs = await repo.list(filters)

    return logs
