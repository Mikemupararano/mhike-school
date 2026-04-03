from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.school import School

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_school(
    name: str,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(School).where(School.name == name))
    if res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="School already exists",
        )

    school = School(name=name)
    db.add(school)
    await db.commit()
    await db.refresh(school)
    return school


@router.get("")
async def list_schools(
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(School).order_by(School.id))
    return list(res.scalars().all())
