from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.school_service import SchoolService

router = APIRouter()


@router.get("/")
async def list_schools(db: AsyncSession = Depends(get_db)):
    return await SchoolService.list_schools(db)
