"""Multi-skill talent search route (Endpoint 5)."""

from typing import Annotated

from asyncpg import Connection
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_connection
from app.models.search import TalentSearchResponse
from app.services import search_service as svc

router = APIRouter(prefix="/tm/talent", tags=["Talent Search"])

DbConn = Annotated[Connection, Depends(get_connection)]


@router.get("/search", response_model=TalentSearchResponse)
async def talent_search(
    conn: DbConn,
    skills: str = Query(max_length=500, description="Comma-separated skill names (e.g., 'Python,SQL') — max 10 skills"),
    min_proficiency: float = Query(default=3, ge=0, le=5, description="Minimum proficiency for each skill"),
):
    """**Endpoint 5** — Find employees who have ALL specified skills at minimum proficiency.

    This is an AND search: only employees with every listed skill are returned.
    """
    skill_names = [s.strip() for s in skills.split(",") if s.strip()]
    if len(skill_names) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 skills allowed per search")
    return await svc.multi_skill_search(conn, skill_names, int(min_proficiency))
