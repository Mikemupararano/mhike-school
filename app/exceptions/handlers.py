from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError


def error_response(
    *,
    status_code: int,
    message: str,
    error_code: str,
    details: object | None = None,
) -> JSONResponse:
    payload: dict[str, object] = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
        },
    }

    if details is not None:
        payload["error"]["details"] = details

    return JSONResponse(status_code=status_code, content=payload)


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    return error_response(
        status_code=exc.status_code,
        message=str(exc.detail),
        error_code="HTTP_ERROR",
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Validation failed.",
        error_code="VALIDATION_ERROR",
        details=exc.errors(),
    )


async def pydantic_validation_exception_handler(
    request: Request,
    exc: ValidationError,
) -> JSONResponse:
    return error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Validation failed.",
        error_code="VALIDATION_ERROR",
        details=exc.errors(),
    )


async def integrity_error_handler(
    request: Request,
    exc: IntegrityError,
) -> JSONResponse:
    return error_response(
        status_code=status.HTTP_409_CONFLICT,
        message="A database constraint was violated.",
        error_code="INTEGRITY_ERROR",
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Internal server error.",
        error_code="INTERNAL_SERVER_ERROR",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
