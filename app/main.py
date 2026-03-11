from fastapi import FastAPI
from app.core.config import settings
from app.api.routers import api_router

from app.db.session import AsyncSessionLocal
from app.core.bootstrap import bootstrap_admin

app = FastAPI(title=settings.app_name)
app.include_router(api_router)


@app.on_event("startup")
async def on_startup():
    async with AsyncSessionLocal() as db:
        await bootstrap_admin(
            db=db,
            enabled=settings.bootstrap_admin_enabled,
            email=settings.bootstrap_admin_email,
            password=settings.bootstrap_admin_password,
        )


@app.get("/", tags=["root"])
def root():
    return {"app": settings.app_name, "status": "ok"}
