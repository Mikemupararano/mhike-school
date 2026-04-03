from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.v1.api import api_router
from app.core.bootstrap import bootstrap_admin
from app.core.config import settings
from app.db.session import AsyncSessionLocal

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSessionLocal() as db:
        await bootstrap_admin(
            db=db,
            enabled=settings.bootstrap_admin_enabled,
            email=settings.bootstrap_admin_email,
            password=settings.bootstrap_admin_password,
        )
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": False},
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

    # Ensure components exist
    components = openapi_schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})

    security_schemes["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }

    # Apply Bearer auth globally
    openapi_schema["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ✅ Register API routes
app.include_router(api_router, prefix=API_PREFIX)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    return {
        "app": settings.app_name,
        "status": "ok",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "api_prefix": API_PREFIX,
    }
