from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.api.deps import require_role
from app.models import User

router = APIRouter()


@router.patch("/users/{user_id}/role")
async def set_user_role(
    user_id: int,
    role: str,  # "student" | "teacher" | "admin"
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    if role not in {"student", "teacher", "admin"}:
        raise HTTPException(status_code=400, detail="Invalid role")

    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = role
    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "email": user.email, "role": user.role}
