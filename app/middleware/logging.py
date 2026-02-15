"""Structured access logging middleware."""

import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("tm.access")


def _mask_api_key(key: str | None) -> str:
    """Show first 4 chars of an API key, mask the rest."""
    if not key:
        return "-"
    if len(key) <= 4:
        return "****"
    return key[:4] + "****"


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Log every request in structured key=value format."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        # Extract client IP — prefer X-Forwarded-For (CF Go Router sets this)
        client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if not client_ip:
            client_ip = request.client.host if request.client else "-"

        api_key = _mask_api_key(request.headers.get("x-api-key"))
        query = str(request.url.query) if request.url.query else "-"

        logger.info(
            "method=%s path=%s status=%d duration_ms=%.1f client_ip=%s api_key=%s query=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            client_ip,
            api_key,
            query,
        )

        return response
