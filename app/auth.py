"""API Key authentication dependency."""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    api_key: str | None = Security(_api_key_header),
) -> str | None:
    """Validate the X-API-Key header.

    When ``settings.api_keys`` is empty, authentication is disabled —
    this preserves local-dev convenience and keeps tests passing without
    modification.  Auth is only enforced when keys are configured via
    the ``API_KEYS`` environment variable.
    """
    # Auth disabled — no keys configured
    if not settings.api_keys:
        return None

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key — include an X-API-Key header",
        )

    if api_key not in settings.api_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key
