"""Skill-centric API routes (Endpoints 3, 4, 6, 7, 9, 11)."""

from enum import Enum
from typing import Annotated

from asyncpg import Connection
from fastapi import APIRouter, Depends, Query

from app.database import get_connection
from app.models.skill import (
    EvidenceBackedResponse,
    SkillAdjacencyResponse,
    SkillCatalogResponse,
    SkillCoverageResponse,
    StaleSkillsResponse,
    TopExpertsResponse,
)
from app.services import skill_service as svc

router = APIRouter(prefix="/tm/skills", tags=["Skills"])

DbConn = Annotated[Connection, Depends(get_connection)]


class SkillCategory(str, Enum):
    technical = "technical"
    functional = "functional"
    leadership = "leadership"
    domain = "domain"
    tool = "tool"
    other = "other"


@router.get("", response_model=SkillCatalogResponse)
async def browse_skills(
    conn: DbConn,
    category: SkillCategory | None = Query(default=None, description="Filter by category"),
    search: str | None = Query(default=None, max_length=200, description="Search skill name or description (case-insensitive)"),
):
    """**Endpoint 11** — Browse the skill taxonomy catalog with optional filters."""
    return await svc.browse_skills(conn, category.value if category else None, search)


@router.get("/{skill_id}/experts", response_model=TopExpertsResponse)
async def get_top_experts(
    skill_id: float,
    conn: DbConn,
    min_proficiency: float = Query(default=4, ge=0, le=5, description="Minimum proficiency level"),
    limit: float = Query(default=20, ge=1, le=100, description="Max results to return"),
):
    """**Endpoint 3** — Who are the top experts in this skill?"""
    return await svc.get_top_experts(conn, int(skill_id), int(min_proficiency), int(limit))


@router.get("/{skill_id}/coverage", response_model=SkillCoverageResponse)
async def get_skill_coverage(
    skill_id: float,
    conn: DbConn,
    min_proficiency: float = Query(default=3, ge=0, le=5, description="Minimum proficiency for coverage count"),
):
    """**Endpoint 4** — How many employees have this skill? Proficiency distribution histogram."""
    return await svc.get_skill_coverage(conn, int(skill_id), int(min_proficiency))


@router.get("/{skill_id}/candidates", response_model=EvidenceBackedResponse)
async def get_evidence_backed_candidates(
    skill_id: float,
    conn: DbConn,
    min_proficiency: float = Query(default=3, ge=0, le=5, description="Minimum proficiency level"),
    min_evidence_strength: float = Query(default=4, ge=1, le=5, description="Minimum evidence signal strength"),
    limit: float = Query(default=20, ge=1, le=100, description="Max candidates to return"),
):
    """**Endpoint 6** — Who has this skill with strong evidence to back it up?"""
    return await svc.get_evidence_backed_candidates(conn, int(skill_id), int(min_proficiency), int(min_evidence_strength), int(limit))


@router.get("/{skill_id}/stale", response_model=StaleSkillsResponse)
async def get_stale_skills(
    skill_id: float,
    conn: DbConn,
    older_than_days: float = Query(default=365, ge=1, description="Skills not updated in this many days"),
):
    """**Endpoint 7** — Which employees have this skill but it hasn't been validated recently?"""
    return await svc.get_stale_skills(conn, int(skill_id), int(older_than_days))


@router.get("/{skill_id}/cooccurring", response_model=SkillAdjacencyResponse)
async def get_cooccurring_skills(
    skill_id: float,
    conn: DbConn,
    min_proficiency: float = Query(default=3, ge=0, le=5, description="Minimum proficiency to consider"),
    top: float = Query(default=20, ge=1, le=50, description="Number of co-occurring skills to return"),
):
    """**Endpoint 9** — For employees strong in this skill, what other skills do they commonly have?"""
    return await svc.get_cooccurring_skills(conn, int(skill_id), int(min_proficiency), int(top))
