"""Talent Management Skills API — FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth import require_api_key
from app.config import settings
from app.database import create_pool, close_pool
from app.middleware.logging import AccessLogMiddleware
from app.routers import employees, skills, talent_search, orgs

DESCRIPTION = """
## Talent Management Skills API

A demo REST API exposing **12 business questions** about employee skills,
proficiency, evidence, and talent search.

Built on top of an HR employee database, the TM system maintains its own
skill catalog, employee-skill assignments, and evidence records in the `tm` schema.

### Endpoint groups

| Group | Endpoints | Description |
|-------|-----------|-------------|
| **Employees** | 1, 2, 8, 10 | Skill profiles, evidence, skill passport |
| **Skills** | 3, 4, 6, 7, 9, 11 | Experts, coverage, candidates, staleness, co-occurrence, taxonomy |
| **Talent Search** | 5 | Multi-skill AND search across the workforce |
| **Organizations** | 12 | Org-level skill summaries with hierarchy traversal |
"""

TAGS_METADATA = [
    {"name": "Employees", "description": "Employee-centric endpoints — skill profiles, evidence, and skill passports."},
    {"name": "Skills", "description": "Skill-centric endpoints — experts, coverage, staleness, co-occurrence, and taxonomy browsing."},
    {"name": "Talent Search", "description": "Multi-skill AND search to find employees matching multiple skill criteria."},
    {"name": "Organizations", "description": "Org-level skill summaries using recursive hierarchy traversal."},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup/shutdown: create and close the DB pool."""
    await create_pool()
    yield
    await close_pool()


app = FastAPI(
    title="Talent Management Skills API",
    description=DESCRIPTION,
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=TAGS_METADATA,
)

# ── Rate limiting ────────────────────────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_default] if settings.rate_limit_enabled else [],
    enabled=settings.rate_limit_enabled,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["Authorization", "X-API-Key", "Content-Type"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add standard security headers to every response."""

    HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Cache-Control": "no-store",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' https://cdn.tailwindcss.com 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        ),
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for header, value in self.HEADERS.items():
            response.headers[header] = value
        return response


app.add_middleware(AccessLogMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Return a clean JSON response for unexpected errors."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


_auth = [Depends(require_api_key)]
app.include_router(employees.router, dependencies=_auth)
app.include_router(skills.router, dependencies=_auth)
app.include_router(talent_search.router, dependencies=_auth)
app.include_router(orgs.router, dependencies=_auth)


app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to the interactive API explorer."""
    return RedirectResponse(url="/static/index.html")


@app.get("/health", tags=["Health"])
async def health():
    """Health check — exempt from API key auth (used by CF health probes)."""
    from app.database import pool

    if pool is None:
        return {"status": "unhealthy", "db": "pool not initialised"}
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "healthy", "db": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "db": str(e)}
