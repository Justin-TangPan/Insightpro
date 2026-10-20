"""FastAPI middleware: catch unhandled exceptions, log them, return sanitized JSON.

Prevents internal error details from leaking to clients.
HTTPException instances pass through unchanged (FastAPI handles those).
"""
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("insight.errors")


class SanitizingErrorHandler(BaseHTTPMiddleware):
    """Catch-all middleware that sanitizes unhandled exception responses."""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            logger.exception(
                "Unhandled exception on %s %s", request.method, request.url.path
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Service temporarily unavailable, please try again later"},
            )
