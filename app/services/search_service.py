"""Business logic for multi-skill talent search (Endpoint 5)."""

from collections import defaultdict

from asyncpg import Connection
from fastapi import HTTPException

from app.models.search import (
    MatchedSkill,
    TalentSearchHit,
    TalentSearchQuery,
    TalentSearchResponse,
)
from app.queries import search_queries as Q


async def multi_skill_search(
    conn: Connection, skill_names: list[str], min_proficiency: int,
) -> TalentSearchResponse:
    """Endpoint 5: Find employees with ALL specified skills at min proficiency."""
    if not skill_names:
        raise HTTPException(status_code=400, detail="At least one skill name is required")

    # Resolve skill names to IDs (case-insensitive)
    rows = await conn.fetch(Q.RESOLVE_SKILL_NAMES, skill_names)
    if not rows:
        raise HTTPException(status_code=404, detail=f"None of the specified skills found: {skill_names}")

    found_map = {r["name"].lower(): (r["skill_id"], r["name"]) for r in rows}
    missing = [n for n in skill_names if n.lower() not in found_map]
    if missing:
        raise HTTPException(status_code=404, detail=f"Skills not found: {missing}")

    skill_ids = [sid for sid, _ in found_map.values()]
    canonical_names = [name for _, name in found_map.values()]
    num_skills = len(skill_ids)

    # Find employees who have ALL skills at min_proficiency
    emp_rows = await conn.fetch(Q.MULTI_SKILL_SEARCH, skill_ids, min_proficiency, num_skills)

    if not emp_rows:
        return TalentSearchResponse(
            query=TalentSearchQuery(
                skill_names=canonical_names, min_proficiency=min_proficiency, results_count=0,
            ),
            results=[],
        )

    # Fetch per-skill details for all matched employees
    emp_ids = [r["employee_id"] for r in emp_rows]
    detail_rows = await conn.fetch(Q.MATCHED_SKILL_DETAILS, emp_ids, skill_ids)

    skills_by_emp: dict[str, list[MatchedSkill]] = defaultdict(list)
    for r in detail_rows:
        d = dict(r)
        emp_id = d.pop("employee_id")
        skills_by_emp[emp_id].append(MatchedSkill(**d))

    results = [
        TalentSearchHit(
            employee_id=r["employee_id"],
            display_name=r["display_name"],
            job_title=r["job_title"],
            org_name=r["org_name"],
            seniority_level=r["seniority_level"],
            matched_skills=skills_by_emp.get(r["employee_id"], []),
        )
        for r in emp_rows
    ]

    return TalentSearchResponse(
        query=TalentSearchQuery(
            skill_names=canonical_names, min_proficiency=min_proficiency, results_count=len(results),
        ),
        results=results,
    )
