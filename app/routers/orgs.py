"""Org-centric skill routes (Endpoint 12)."""

from typing import Annotated

from asyncpg import Connection
from fastapi import APIRouter, Depends, Path, Query

from app.database import get_connection
from app.models.org import OrgSkillExpertsResponse, OrgSkillSummaryResponse
from app.services import org_service as svc

router = APIRouter(prefix="/tm/orgs", tags=["Organizations"])

DbConn = Annotated[Connection, Depends(get_connection)]
OrgId = Annotated[str, Path(pattern=r"^ORG\d{1,4}[A-Z]?$", description="Org unit ID (e.g. ORG030, ORG031B)")]


@router.get("/{org_unit_id}/skills/summary", response_model=OrgSkillSummaryResponse)
async def get_org_skill_summary(
    org_unit_id: OrgId,
    conn: DbConn,
    limit: int = Query(default=20, ge=1, le=100, description="Number of top skills to return"),
):
    """**Endpoint 12a** — What are the top skills in this org unit (including child orgs)?"""
    return await svc.get_org_skill_summary(conn, org_unit_id, limit)


@router.get("/{org_unit_id}/skills/{skill_id}/experts", response_model=OrgSkillExpertsResponse)
async def get_org_skill_experts(
    org_unit_id: OrgId,
    skill_id: int,
    conn: DbConn,
    min_proficiency: int = Query(default=3, ge=0, le=5, description="Minimum proficiency level"),
    limit: int = Query(default=20, ge=1, le=100, description="Max results"),
):
    """**Endpoint 12b** — Who in this org unit has this skill at minimum proficiency?"""
    return await svc.get_org_skill_experts(conn, org_unit_id, skill_id, min_proficiency, limit)
