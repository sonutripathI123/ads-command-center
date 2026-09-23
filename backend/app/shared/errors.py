"""SHARED (owner: P00) — error conventions.

Modules raise AppError subclasses; the handler renders the standard envelope:
    {"error": {"code": "...", "message": "...", "module_id": "P08", "request_id": "...", "details": {...}}}
Public interface: AppError, NotFoundError, ValidationFailed, PermissionDenied, FeatureDisabled, register_error_handlers
"""
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.shared.logging import get_logger, request_id_var

log = get_logger("P00")


class AppError(Exception):
    status_code = 400
    code = "app_error"

    def __init__(self, message: str, *, module_id: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.module_id = module_id
        self.details = details or {}


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ValidationFailed(AppError):
    status_code = 422
    code = "validation_failed"


class PermissionDenied(AppError):
    status_code = 403
    code = "permission_denied"


class FeatureDisabled(AppError):
    status_code = 409
    code = "feature_disabled"


def _envelope(status: int, code: str, message: str, module_id: str | None, details: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "module_id": module_id,
                           "request_id": request_id_var.get(), "details": details or {}}},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        log.warning("app_error", extra={"code": exc.code, "error_module": exc.module_id, "detail": exc.message})
        return _envelope(exc.status_code, exc.code, exc.message, exc.module_id, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        return _envelope(422, "request_invalid", "Request validation failed", None, {"errors": exc.errors()})

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        log.exception("unhandled_error")
        return _envelope(500, "internal_error", "Internal server error", None)
