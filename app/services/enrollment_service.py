from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.class_group import ClassGroup
from app.models.enrollment import Enrollment
from app.models.user import User
from app.schemas.enrollment import EnrollmentCreate


class EnrollmentService:
    @staticmethod
    async def add_student_to_class(
        db: AsyncSession,
        payload: EnrollmentCreate,
        school_id: int,
    ):
        class_result = await db.execute(
            select(ClassGroup).where(
                ClassGroup.id == payload.class_id,
                ClassGroup.school_id == school_id,
            )
        )
        class_group = class_result.scalar_one_or_none()
        if class_group is None:
            raise ValueError("Class not found")

        user_result = await db.execute(
            select(User).where(
                User.id == payload.user_id,
                User.school_id == school_id,
            )
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            raise ValueError("User not found")

        if user.role != "student":
            raise ValueError("Only students can be enrolled in a class")

        existing_result = await db.execute(
            select(Enrollment).where(
                Enrollment.user_id == payload.user_id,
                Enrollment.class_id == payload.class_id,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            raise ValueError("Student is already enrolled in this class")

        enrollment = Enrollment(
            user_id=payload.user_id,
            class_id=payload.class_id,
        )

        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)

        return enrollment
