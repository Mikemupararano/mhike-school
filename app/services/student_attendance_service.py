from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.student_attendance import StudentAttendanceRepository
from app.schemas.student_attendance import (
    StudentAttendanceHistoryRecord,
    StudentAttendanceProfile,
)


class StudentAttendanceService:
    def __init__(self, db: AsyncSession):
        self.repo = StudentAttendanceRepository(db)

    async def get_student_profile(
        self,
        school_id: int,
        student_id: int,
    ) -> StudentAttendanceProfile:
        student = await self.repo.get_student_by_id(student_id)

        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found.",
            )

        rows = await self.repo.list_student_history(
            school_id=school_id,
            student_id=student_id,
        )

        present = 0
        late = 0
        authorised_absence = 0
        unauthorised_absence = 0

        history: list[StudentAttendanceHistoryRecord] = []

        for record, session, class_name in rows:
            status_value = str(record.status)

            if status_value == "present":
                present += 1
            elif status_value == "late":
                late += 1
            elif status_value == "authorised_absence":
                authorised_absence += 1
            elif status_value == "unauthorised_absence":
                unauthorised_absence += 1

            history.append(
                StudentAttendanceHistoryRecord(
                    record_id=record.id,
                    attendance_session_id=record.attendance_session_id,
                    session_date=session.session_date,
                    session_type=str(session.session_type),
                    class_group_id=session.class_group_id,
                    class_name=class_name,
                    status=status_value,
                    notes=record.notes,
                    marked_by_id=record.marked_by_id,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )
            )

        total_records = len(history)

        attendance_percentage = (
            round(((present + late) / total_records) * 100, 2)
            if total_records > 0
            else 0.0
        )

        return StudentAttendanceProfile(
            student_id=student.id,
            student_name=getattr(student, "email", None),
            school_id=school_id,
            total_records=total_records,
            present=present,
            late=late,
            authorised_absence=authorised_absence,
            unauthorised_absence=unauthorised_absence,
            attendance_percentage=attendance_percentage,
            history=history,
        )
