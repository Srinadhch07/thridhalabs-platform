"""Application error type and JSON exception handlers.

Every error response has the same shape and never leaks internals:

    {"error": {"code": "...", "message": "..."}}
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

log = get_logger("errors")


class AppError(Exception):
    """Controlled, client-safe application error."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers or {}


def error_payload(code: str, message: str, **extra: object) -> dict:
    body: dict = {"code": code, "message": message}
    if extra:
        body.update(extra)
    return {"error": body}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(exc.code, exc.message),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Field messages only — raw input values are deliberately NOT echoed,
        # because request bodies can contain passwords.
        fields: dict[str, str] = {}
        for err in exc.errors():
            location = ".".join(str(part) for part in err.get("loc", ()) if part != "body")
            fields[location or "body"] = err.get("msg", "invalid value")
        return JSONResponse(
            status_code=422,
            content=jsonable_encoder(
                error_payload(
                    "VALIDATION_ERROR",
                    "Request validation failed",
                    fields=fields,
                )
            ),
        )
