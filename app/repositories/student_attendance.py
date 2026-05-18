from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_record import AttendanceRecord
from app.models.attendance_session import AttendanceSession
from app.models.class_group import ClassGroup
from app.models.user import User


class StudentAttendanceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_student_by_id(
        self,
        student_id: int,
    ) -> User | None:
        result = await self.db.execute(select(User).where(User.id == student_id))

        return result.scalar_one_or_none()

    async def list_student_history(
        self,
        school_id: int,
        student_id: int,
    ) -> list[tuple[AttendanceRecord, AttendanceSession, str | None]]:
        result = await self.db.execute(
            select(
                AttendanceRecord,
                AttendanceSession,
                ClassGroup.name,
            )
            .join(
                AttendanceSession,
                AttendanceRecord.attendance_session_id == AttendanceSession.id,
            )
            .outerjoin(
                ClassGroup,
                AttendanceSession.class_group_id == ClassGroup.id,
            )
            .where(
                AttendanceSession.school_id == school_id,
                AttendanceRecord.student_id == student_id,
            )
            .order_by(
                AttendanceSession.session_date.desc(),
                AttendanceSession.session_type.asc(),
                AttendanceRecord.id.desc(),
            )
        )

        return list(result.all())
