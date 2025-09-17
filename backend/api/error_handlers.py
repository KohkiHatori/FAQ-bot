"""
Centralized error handling for the API.
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.applications import FastAPI
from core.exceptions import (
    FAQBotException,
    DatabaseError,
    ValidationError,
    NotFoundError,
    PermissionError,
    CacheError,
    ExternalServiceError,
)


def register_error_handlers(app: FastAPI):
    """Register all error handlers with the FastAPI app."""

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Validation Error",
                "message": str(exc),
                "type": "validation_error",
            },
        )

    @app.exception_handler(NotFoundError)
    async def not_found_error_handler(request: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=404,
            content={
                "error": "Not Found",
                "message": str(exc),
                "type": "not_found_error",
            },
        )

    @app.exception_handler(PermissionError)
    async def permission_error_handler(request: Request, exc: PermissionError):
        return JSONResponse(
            status_code=403,
            content={
                "error": "Permission Denied",
                "message": str(exc),
                "type": "permission_error",
            },
        )

    @app.exception_handler(DatabaseError)
    async def database_error_handler(request: Request, exc: DatabaseError):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Database Error",
                "message": "An internal database error occurred",
                "type": "database_error",
            },
        )

    @app.exception_handler(CacheError)
    async def cache_error_handler(request: Request, exc: CacheError):
        return JSONResponse(
            status_code=503,
            content={
                "error": "Cache Error",
                "message": str(exc),
                "type": "cache_error",
            },
        )

    @app.exception_handler(ExternalServiceError)
    async def external_service_error_handler(
        request: Request, exc: ExternalServiceError
    ):
        return JSONResponse(
            status_code=502,
            content={
                "error": "External Service Error",
                "message": str(exc),
                "type": "external_service_error",
            },
        )

    @app.exception_handler(FAQBotException)
    async def faq_bot_error_handler(request: Request, exc: FAQBotException):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Error",
                "message": str(exc),
                "type": "faq_bot_error",
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP Error",
                "message": exc.detail,
                "type": "http_error",
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "type": "general_error",
            },
        )
