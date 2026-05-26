"""Structured error handling for the knowledge-graph service."""

from __future__ import annotations

import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base application error with HTTP status code."""

    def __init__(self, message: str, status_code: int = 500, detail: str = ""):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class ServiceUnavailableError(AppError):
    """Raised when an upstream dependency is unavailable or misconfigured."""

    def __init__(self, service: str, detail: str = ""):
        super().__init__(
            message=f"{service} is currently unavailable",
            status_code=503,
            detail=detail,
        )


class TooManyRequestsError(AppError):
    """Raised when the application is saturated and cannot accept more work."""

    def __init__(self, detail: str = ""):
        super().__init__(
            message="Request capacity is saturated",
            status_code=429,
            detail=detail,
        )


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        logger.warning(
            "Application error on %s %s: %s detail=%s",
            request.method,
            request.url.path,
            exc.message,
            exc.detail,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message, "detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled exception on %s %s: %s\n%s",
            request.method,
            request.url.path,
            exc,
            traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if logger.isEnabledFor(logging.DEBUG) else "",
            },
        )
