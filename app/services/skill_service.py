"""Business logic for skill-centric endpoints."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from asyncpg import Connection
from fastapi import HTTPException

from app.models.evidence import EvidenceItem
from app.models.skill import (
    CooccurringSkill,
    EvidenceBackedCandidate,
    EvidenceBackedResponse,
    ProficiencyBucket,
    SkillAdjacencyResponse,
    SkillCatalogResponse,
    SkillCoverageResponse,
    SkillExpert,
    SkillInfo,
    StaleSkillEntry,
    StaleSkillsResponse,
    TopExpertsResponse,
)
from app.queries import skill_queries as Q


async def _get_skill_or_404(conn: Connection, skill_id: int) -> SkillInfo:
    """Fetch skill metadata or raise 404."""
    row = await conn.fetchrow(Q.GET_SKILL_INFO, skill_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Skill {skill_id} not found or inactive")
    return SkillInfo(**dict(row))


async def get_top_experts(
    conn: Connection, skill_id: int, min_proficiency: int, limit: int
) -> TopExpertsResponse:
    """Endpoint 3: Top experts for a skill."""
    skill = await _get_skill_or_404(conn, skill_id)
    rows = await conn.fetch(Q.GET_TOP_EXPERTS, skill_id, min_proficiency, limit)
    total = await conn.fetchval(Q.COUNT_EXPERTS, skill_id, min_proficiency)
    experts = [SkillExpert(**dict(r)) for r in rows]
    return TopExpertsResponse(
        skill=skill, experts=experts, min_proficiency=min_proficiency, total_matching=total,
    )


async def get_skill_coverage(
    conn: Connection, skill_id: int, min_proficiency: int
) -> SkillCoverageResponse:
    """Endpoint 4: Skill coverage and proficiency distribution."""
    skill = await _get_skill_or_404(conn, skill_id)

    dist_rows = await conn.fetch(Q.SKILL_DISTRIBUTION, skill_id)
    total = await conn.fetchval(Q.SKILL_TOTAL_COUNT, skill_id)
    at_min = await conn.fetchval(Q.SKILL_COVERAGE_COUNT, skill_id, min_proficiency)

    # Build full 0-5 histogram (fill missing levels with 0)
    dist_map = {r["proficiency"]: r["count"] for r in dist_rows}
    distribution = [ProficiencyBucket(proficiency=p, count=dist_map.get(p, 0)) for p in range(6)]

    return SkillCoverageResponse(
        skill=skill,
        total_employees=total,
        employees_at_min=at_min,
        min_proficiency=min_proficiency,
        distribution=distribution,
    )


async def get_evidence_backed_candidates(
    conn: Connection, skill_id: int, min_proficiency: int, min_evidence_strength: int, limit: int,
) -> EvidenceBackedResponse:
    """Endpoint 6: Candidates with skill + strong evidence."""
    skill = await _get_skill_or_404(conn, skill_id)

    # Get candidates who have both the skill and strong evidence
    cand_rows = await conn.fetch(
        Q.GET_EVIDENCE_BACKED_CANDIDATES, skill_id, min_proficiency, min_evidence_strength,
    )
    if not cand_rows:
        return EvidenceBackedResponse(
            skill=skill, candidates=[], min_proficiency=min_proficiency,
            min_evidence_strength=min_evidence_strength,
        )

    # Sort by proficiency/confidence and apply limit
    cand_rows = sorted(cand_rows, key=lambda r: (-r["proficiency"], -r["confidence"]))[:limit]
    emp_ids = [r["employee_id"] for r in cand_rows]

    # Batch-fetch strong evidence for all candidates
    ev_rows = await conn.fetch(
        Q.GET_STRONG_EVIDENCE_FOR_EMPLOYEES, skill_id, min_evidence_strength, emp_ids,
    )
    evidence_by_emp: dict[str, list[EvidenceItem]] = defaultdict(list)
    for r in ev_rows:
        d = dict(r)
        emp_id = d.pop("employee_id")
        evidence_by_emp[emp_id].append(EvidenceItem(**d))

    candidates = [
        EvidenceBackedCandidate(
            employee_id=r["employee_id"],
            display_name=r["display_name"],
            job_title=r["job_title"],
            proficiency=r["proficiency"],
            confidence=r["confidence"],
            top_evidence=evidence_by_emp.get(r["employee_id"], []),
        )
        for r in cand_rows
    ]

    return EvidenceBackedResponse(
        skill=skill, candidates=candidates,
        min_proficiency=min_proficiency, min_evidence_strength=min_evidence_strength,
    )


async def get_stale_skills(
    conn: Connection, skill_id: int, older_than_days: int
) -> StaleSkillsResponse:
    """Endpoint 7: Employees whose skill record is stale."""
    skill = await _get_skill_or_404(conn, skill_id)
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    rows = await conn.fetch(Q.GET_STALE_SKILLS, skill_id, cutoff)
    entries = [StaleSkillEntry(**dict(r)) for r in rows]
    return StaleSkillsResponse(
        skill=skill, stale_entries=entries, older_than_days=older_than_days, total_stale=len(entries),
    )


async def get_cooccurring_skills(
    conn: Connection, skill_id: int, min_proficiency: int, top: int
) -> SkillAdjacencyResponse:
    """Endpoint 9: Skills that co-occur with the given skill."""
    skill = await _get_skill_or_404(conn, skill_id)
    rows = await conn.fetch(Q.GET_COOCCURRING_SKILLS, skill_id, min_proficiency, top)
    cooccurring = [CooccurringSkill(**dict(r)) for r in rows]
    return SkillAdjacencyResponse(skill=skill, min_proficiency=min_proficiency, cooccurring=cooccurring)


async def browse_skills(conn: Connection, category: str | None, search: str | None) -> SkillCatalogResponse:
    """Endpoint 11: Skill taxonomy browsing with optional filters."""
    rows = await conn.fetch(Q.BROWSE_SKILLS, category, search)
    skills = [SkillInfo(**dict(r)) for r in rows]
    return SkillCatalogResponse(skills=skills, total=len(skills))
