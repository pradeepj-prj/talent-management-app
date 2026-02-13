"""Business logic for org-centric endpoints (Endpoint 12)."""

from asyncpg import Connection
from fastapi import HTTPException

from app.models.org import (
    OrgRef,
    OrgSkillExpert,
    OrgSkillExpertsResponse,
    OrgSkillSummaryEntry,
    OrgSkillSummaryResponse,
)
from app.queries import org_queries as Q
from app.queries import skill_queries as SQ


async def _get_org_or_404(conn: Connection, org_id: str) -> OrgRef:
    """Fetch org_unit_ref or raise 404."""
    row = await conn.fetchrow(Q.GET_ORG_REF, org_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Org unit {org_id} not found")
    return OrgRef(**dict(row))


async def get_org_skill_summary(
    conn: Connection, org_id: str, limit: int,
) -> OrgSkillSummaryResponse:
    """Endpoint 12a: Top skills across an org unit (including children)."""
    org = await _get_org_or_404(conn, org_id)

    skill_rows = await conn.fetch(Q.ORG_SKILL_SUMMARY, org_id, limit)
    emp_count = await conn.fetchval(Q.ORG_EMPLOYEE_COUNT, org_id)

    top_skills = [OrgSkillSummaryEntry(**dict(r)) for r in skill_rows]

    return OrgSkillSummaryResponse(
        org=org,
        includes_children=True,
        total_profiled_employees=emp_count,
        top_skills=top_skills,
    )


async def get_org_skill_experts(
    conn: Connection, org_id: str, skill_id: int, min_proficiency: int, limit: int,
) -> OrgSkillExpertsResponse:
    """Endpoint 12b: Experts for a specific skill within an org unit."""
    org = await _get_org_or_404(conn, org_id)

    # Verify skill exists
    skill_row = await conn.fetchrow(SQ.GET_SKILL_INFO, skill_id)
    if not skill_row:
        raise HTTPException(status_code=404, detail=f"Skill {skill_id} not found or inactive")

    expert_rows = await conn.fetch(Q.ORG_SKILL_EXPERTS, org_id, skill_id, min_proficiency, limit)
    total = await conn.fetchval(Q.ORG_SKILL_EXPERT_COUNT, org_id, skill_id, min_proficiency)

    experts = [OrgSkillExpert(**dict(r)) for r in expert_rows]

    return OrgSkillExpertsResponse(
        org=org,
        skill_id=skill_id,
        skill_name=skill_row["name"],
        min_proficiency=min_proficiency,
        experts=experts,
        total_matching=total,
    )
