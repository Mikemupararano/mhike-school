from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.class_group import ClassGroup
from app.models.enrollment import Enrollment
from app.models.user import User, UserRole


class ClassService:
    @staticmethod
    def has_role(user: User, role: UserRole) -> bool:
        return role.value in set(user.roles)

    @staticmethod
    async def get_class(
        db: AsyncSession,
        class_id: int,
        school_id: int,
    ) -> ClassGroup:
        result = await db.execute(
            select(ClassGroup)
            .options(selectinload(ClassGroup.teacher))
            .where(
                ClassGroup.id == class_id,
                ClassGroup.school_id == school_id,
            )
        )
        class_group = result.scalar_one_or_none()

        if not class_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Class not found",
            )

        return class_group

    @staticmethod
    async def list_classes_by_school(
        db: AsyncSession,
        school_id: int,
    ) -> list[ClassGroup]:
        result = await db.execute(
            select(ClassGroup)
            .options(selectinload(ClassGroup.teacher))
            .where(ClassGroup.school_id == school_id)
            .order_by(ClassGroup.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_class(
        db: AsyncSession,
        name: str,
        school_id: int,
        teacher_id: int | None = None,
    ) -> ClassGroup:
        existing_result = await db.execute(
            select(ClassGroup).where(
                ClassGroup.name == name,
                ClassGroup.school_id == school_id,
            )
        )
        existing_class = existing_result.scalar_one_or_none()

        if existing_class is not None:
            raise ValueError("A class with this name already exists in this school")

        if teacher_id is not None:
            teacher_result = await db.execute(
                select(User).where(
                    User.id == teacher_id,
                    User.school_id == school_id,
                )
            )
            teacher = teacher_result.scalar_one_or_none()

            if teacher is None or not ClassService.has_role(teacher, UserRole.TEACHER):
                raise ValueError("Invalid teacher for this school")

        class_group = ClassGroup(
            name=name,
            school_id=school_id,
            teacher_id=teacher_id,
        )

        db.add(class_group)
        await db.flush()

        return class_group

    @staticmethod
    async def assign_teacher(
        db: AsyncSession,
        class_id: int,
        teacher_id: int,
        school_id: int,
    ) -> ClassGroup:
        class_group = await ClassService.get_class(db, class_id, school_id)

        teacher_result = await db.execute(
            select(User).where(
                User.id == teacher_id,
                User.school_id == school_id,
            )
        )
        teacher = teacher_result.scalar_one_or_none()

        if teacher is None or not ClassService.has_role(teacher, UserRole.TEACHER):
            raise ValueError("Invalid teacher")

        class_group.teacher_id = teacher_id

        await db.flush()

        return class_group

    @staticmethod
    async def get_students_in_class(
        db: AsyncSession,
        class_id: int,
        school_id: int,
    ) -> list[User]:
        class_group = await ClassService.get_class(db, class_id, school_id)

        result = await db.execute(
            select(User)
            .join(Enrollment, Enrollment.user_id == User.id)
            .where(
                Enrollment.class_id == class_group.id,
                User.school_id == school_id,
            )
            .order_by(User.id)
        )

        users = list(result.scalars().all())
        return [user for user in users if ClassService.has_role(user, UserRole.STUDENT)]

    @staticmethod
    async def add_student(
        db: AsyncSession,
        class_id: int,
        student_id: int,
        school_id: int,
    ) -> Enrollment:
        class_group = await ClassService.get_class(db, class_id, school_id)

        student_result = await db.execute(
            select(User).where(
                User.id == student_id,
                User.school_id == school_id,
            )
        )
        student = student_result.scalar_one_or_none()

        if student is None or not ClassService.has_role(student, UserRole.STUDENT):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid student",
            )

        existing = await db.execute(
            select(Enrollment).where(
                Enrollment.class_id == class_group.id,
                Enrollment.user_id == student_id,
            )
        )

        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student already enrolled",
            )

        enrollment = Enrollment(
            class_id=class_group.id,
            user_id=student_id,
        )

        db.add(enrollment)
        await db.flush()

        return enrollment

    @staticmethod
    async def remove_student(
        db: AsyncSession,
        class_id: int,
        student_id: int,
        school_id: int,
    ) -> None:
        class_group = await ClassService.get_class(db, class_id, school_id)

        result = await db.execute(
            select(Enrollment).where(
                Enrollment.class_id == class_group.id,
                Enrollment.user_id == student_id,
            )
        )
        enrollment = result.scalar_one_or_none()

        if enrollment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrollment not found",
            )

        await db.delete(enrollment)
        await db.flush()
