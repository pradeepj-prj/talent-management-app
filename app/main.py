"""Talent Management Skills API — FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import create_pool, close_pool
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Return a clean JSON response for unexpected errors."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(employees.router)
app.include_router(skills.router)
app.include_router(talent_search.router)
app.include_router(orgs.router)


@app.get("/health", tags=["Health"])
async def health():
    """Health check — confirms the API is running and the DB pool is alive."""
    from app.database import pool

    if pool is None:
        return {"status": "unhealthy", "db": "pool not initialised"}
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "healthy", "db": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "db": str(e)}
