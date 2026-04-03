from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_school_id, get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.user import UserOut
from app.services.school_user_service import SchoolUserService

router = APIRouter()


@router.get("/", response_model=List[UserOut])
async def list_school_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_school_id: int = Depends(get_current_school_id),
):
    return await SchoolUserService.list_users_by_school(db, current_school_id)
