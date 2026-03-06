from fastapi import FastAPI
from app.core.config import settings
from app.api.routers import api_router

app = FastAPI(title=settings.app_name)
app.include_router(api_router)


@app.get("/", tags=["root"])
def root():
    return {"app": settings.app_name, "status": "ok"}
