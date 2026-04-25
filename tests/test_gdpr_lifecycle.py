from datetime import datetime, timedelta, timezone

import pytest

from app.models.user import UserStatus
from app.services.gdpr_service import GDPRService


@pytest.mark.asyncio
async def test_gdpr_anonymises_expired_deactivated_user(db_session, student_user):
    student_user.status = UserStatus.DEACTIVATED
    student_user.is_active = False
    student_user.retention_expires_at = datetime.now(timezone.utc) - timedelta(days=1)

    await db_session.flush()

    count = await GDPRService.anonymise_expired_users(db_session)

    assert count == 1
    assert student_user.status == UserStatus.ANONYMISED
    assert student_user.is_active is False
    assert student_user.email == f'deleted-{student_user.id}@redacted.local'
    assert student_user.hashed_password is None
    assert student_user.anonymised_at is not None


@pytest.mark.asyncio
async def test_gdpr_does_not_anonymise_active_user(db_session, student_user):
    student_user.status = UserStatus.ACTIVE
    student_user.is_active = True
    student_user.retention_expires_at = datetime.now(timezone.utc) - timedelta(days=1)

    await db_session.flush()

    count = await GDPRService.anonymise_expired_users(db_session)

    assert count == 0
    assert student_user.status == UserStatus.ACTIVE
