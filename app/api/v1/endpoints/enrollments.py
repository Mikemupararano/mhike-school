from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_school_id, require_role
from app.db.session import get_db
from app.models import User
from app.models.user import UserRole
from app.schemas.enrollment import EnrollmentCreate, EnrollmentOut
from app.services.enrollment_service import EnrollmentService

router = APIRouter()


@router.post("/", response_model=EnrollmentOut, status_code=status.HTTP_201_CREATED)
async def add_student_to_class(
    payload: EnrollmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(
            UserRole.SCHOOL_ADMIN,
            UserRole.PLATFORM_ADMIN,
            UserRole.TEACHER,
        )
    ),
    current_school_id: int = Depends(get_current_school_id),
):
    try:
        enrollment = await EnrollmentService.add_student_to_class(
            db=db,
            payload=payload,
            school_id=current_school_id,
        )
        await db.commit()
        await db.refresh(enrollment)
        return enrollment
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def remove_student_from_class(
    payload: EnrollmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(
            UserRole.SCHOOL_ADMIN,
            UserRole.PLATFORM_ADMIN,
            UserRole.TEACHER,
        )
    ),
    current_school_id: int = Depends(get_current_school_id),
):
    try:
        await EnrollmentService.remove_student_from_class(
            db=db,
            payload=payload,
            school_id=current_school_id,
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
