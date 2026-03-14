from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.routers import api_router
from app.core.bootstrap import bootstrap_admin
from app.core.config import settings
from app.db.session import AsyncSessionLocal


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    swagger_ui_parameters={"persistAuthorization": True},
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.app_name,
        version="0.1.0",
        description="Mhike School LMS API",
        routes=app.routes,
    )

    openapi_schema.setdefault("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    openapi_schema["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
