from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.class_group import ClassGroup
from app.models.enrollment import Enrollment
from app.models.user import User, UserRole


class ClassService:
    # =========================
    # Get class (school-safe)
    # =========================
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

    # =========================
    # List classes (school)
    # =========================
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

    # =========================
    # Create class
    # =========================
    @staticmethod
    async def create_class(
        db: AsyncSession,
        name: str,
        school_id: int,
        teacher_id: int | None = None,
    ) -> ClassGroup:
        # Optional: validate teacher belongs to school
        if teacher_id:
            teacher_result = await db.execute(
                select(User).where(
                    User.id == teacher_id,
                    User.school_id == school_id,
                    User.role == UserRole.TEACHER,
                )
            )
            teacher = teacher_result.scalar_one_or_none()

            if not teacher:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid teacher for this school",
                )

        class_group = ClassGroup(
            name=name,
            school_id=school_id,
            teacher_id=teacher_id,
        )

        db.add(class_group)
        await db.flush()
        await db.refresh(class_group)

        return class_group

    # =========================
    # Assign teacher
    # =========================
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
                User.role == UserRole.TEACHER,
            )
        )
        teacher = teacher_result.scalar_one_or_none()

        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid teacher",
            )

        class_group.teacher_id = teacher_id

        await db.flush()
        await db.refresh(class_group)

        return class_group

    # =========================
    # Get students in class
    # =========================
    @staticmethod
    async def get_students_in_class(
        db: AsyncSession,
        class_id: int,
        school_id: int,
    ) -> list[User]:
        # ✅ Secure class lookup
        class_group = await ClassService.get_class(db, class_id, school_id)

        result = await db.execute(
            select(User)
            .join(Enrollment, Enrollment.user_id == User.id)
            .where(
                Enrollment.class_id == class_group.id,
                User.school_id == school_id,  # 🔒 extra safety
            )
            .order_by(User.id)
        )

        return list(result.scalars().all())

    # =========================
    # Add student to class
    # =========================
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
                User.role == UserRole.STUDENT,
            )
        )
        student = student_result.scalar_one_or_none()

        if not student:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid student",
            )

        # Prevent duplicate enrollment
        existing = await db.execute(
            select(Enrollment).where(
                Enrollment.class_id == class_id,
                Enrollment.user_id == student_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student already enrolled",
            )

        enrollment = Enrollment(
            class_id=class_id,
            user_id=student_id,
        )

        db.add(enrollment)
        await db.flush()
        await db.refresh(enrollment)

        return enrollment

    # =========================
    # Remove student
    # =========================
    @staticmethod
    async def remove_student(
        db: AsyncSession,
        class_id: int,
        student_id: int,
        school_id: int,
    ) -> None:
        await ClassService.get_class(db, class_id, school_id)

        result = await db.execute(
            select(Enrollment).where(
                Enrollment.class_id == class_id,
                Enrollment.user_id == student_id,
            )
        )
        enrollment = result.scalar_one_or_none()

        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrollment not found",
            )

        await db.delete(enrollment)
        await db.flush()
