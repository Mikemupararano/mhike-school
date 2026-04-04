from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.class_group import ClassGroup
from app.models.enrollment import Enrollment
from app.models.user import User


class ClassService:
    ...

    @staticmethod
    async def get_students_in_class(
        db: AsyncSession,
        class_id: int,
        school_id: int,
    ):
        # Ensure class belongs to school (security)
        class_result = await db.execute(
            select(ClassGroup).where(
                ClassGroup.id == class_id,
                ClassGroup.school_id == school_id,
            )
        )
        class_group = class_result.scalar_one_or_none()

        if class_group is None:
            return None

        result = await db.execute(
            select(User)
            .join(Enrollment, Enrollment.user_id == User.id)
            .where(Enrollment.class_id == class_id)
            .order_by(User.id)
        )

        return result.scalars().all()
