from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_school_id, require_role
from app.db.session import get_db
from app.models import User
from app.schemas.enrollment import EnrollmentCreate, EnrollmentOut
from app.services.enrollment_service import EnrollmentService

router = APIRouter()


@router.post("/", response_model=EnrollmentOut, status_code=201)
async def add_student_to_class(
    payload: EnrollmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher")),
    current_school_id: int = Depends(get_current_school_id),
):
    try:
        return await EnrollmentService.add_student_to_class(
            db,
            payload,
            current_school_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
