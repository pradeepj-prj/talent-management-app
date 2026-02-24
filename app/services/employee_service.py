"""Business logic for employee-centric endpoints."""

from asyncpg import Connection
from fastapi import HTTPException

from app.models.common import EmployeeRef
from app.models.employee import (
    EmployeeEvidenceInventory,
    EmployeeSearchResult,
    EmployeeSkillProfile,
    EmployeeTopSkills,
    SkillEvidenceResponse,
)
from app.models.evidence import EvidenceItem, EvidenceWithSkill
from app.models.skill import EmployeeSkillEntry
from app.queries import employee_queries as Q


async def _get_employee_or_404(conn: Connection, employee_id: str) -> EmployeeRef:
    """Fetch employee_ref or raise 404."""
    row = await conn.fetchrow(Q.GET_EMPLOYEE_REF, employee_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found in TM system")
    return EmployeeRef(**dict(row))


async def get_employee_skills(conn: Connection, employee_id: str) -> EmployeeSkillProfile:
    """Endpoint 1: Full skill profile."""
    emp = await _get_employee_or_404(conn, employee_id)
    rows = await conn.fetch(Q.GET_EMPLOYEE_SKILLS, employee_id)
    skills = [EmployeeSkillEntry(**dict(r)) for r in rows]
    return EmployeeSkillProfile(employee=emp, skills=skills, total_skills=len(skills))


async def get_skill_evidence(conn: Connection, employee_id: str, skill_id: int) -> SkillEvidenceResponse:
    """Endpoint 2: Evidence behind a specific skill."""
    emp = await _get_employee_or_404(conn, employee_id)

    # Check the skill assignment exists
    ctx = await conn.fetchrow(Q.GET_SKILL_CONTEXT, employee_id, skill_id)
    if not ctx:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} does not have skill {skill_id}")

    rows = await conn.fetch(Q.GET_SKILL_EVIDENCE, employee_id, skill_id)
    evidence = [EvidenceItem(**dict(r)) for r in rows]

    return SkillEvidenceResponse(
        employee=emp,
        skill_id=skill_id,
        skill_name=ctx["skill_name"],
        proficiency=ctx["proficiency"],
        confidence=ctx["confidence"],
        evidence=evidence,
    )


async def get_top_skills(conn: Connection, employee_id: str, limit: int) -> EmployeeTopSkills:
    """Endpoint 8: Skill passport — top N skills."""
    emp = await _get_employee_or_404(conn, employee_id)
    rows = await conn.fetch(Q.GET_TOP_SKILLS, employee_id, limit)
    skills = [EmployeeSkillEntry(**dict(r)) for r in rows]
    return EmployeeTopSkills(employee=emp, skills=skills, limit=limit)


async def search_employees_by_name(conn: Connection, name: str, limit: int) -> EmployeeSearchResult:
    """Search employees by name (partial, case-insensitive match)."""
    rows = await conn.fetch(Q.SEARCH_EMPLOYEES_BY_NAME, name, limit)
    total = await conn.fetchval(Q.COUNT_EMPLOYEES_BY_NAME, name)
    employees = [EmployeeRef(**dict(r)) for r in rows]
    return EmployeeSearchResult(employees=employees, total=total)


async def get_evidence_inventory(conn: Connection, employee_id: str) -> EmployeeEvidenceInventory:
    """Endpoint 10: All evidence across all skills."""
    emp = await _get_employee_or_404(conn, employee_id)
    rows = await conn.fetch(Q.GET_ALL_EVIDENCE, employee_id)
    evidence = [EvidenceWithSkill(**dict(r)) for r in rows]
    return EmployeeEvidenceInventory(employee=emp, evidence=evidence, total_items=len(evidence))
