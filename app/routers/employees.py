"""Employee-centric API routes (Endpoints 1, 2, 8, 10)."""

from typing import Annotated

from asyncpg import Connection
from fastapi import APIRouter, Depends, Path, Query

from app.database import get_connection
from app.models.employee import (
    EmployeeEvidenceInventory,
    EmployeeSkillProfile,
    EmployeeTopSkills,
    SkillEvidenceResponse,
)
from app.services import employee_service as svc

router = APIRouter(prefix="/tm/employees", tags=["Employees"])

DbConn = Annotated[Connection, Depends(get_connection)]
EmpId = Annotated[str, Path(pattern=r"^EMP\d{6}$", description="Employee ID (e.g. EMP000001)")]


@router.get("/{employee_id}/skills", response_model=EmployeeSkillProfile)
async def get_employee_skills(employee_id: EmpId, conn: DbConn):
    """**Endpoint 1** — What skills does this employee have, at what proficiency and confidence?"""
    return await svc.get_employee_skills(conn, employee_id)


@router.get("/{employee_id}/skills/{skill_id}/evidence", response_model=SkillEvidenceResponse)
async def get_skill_evidence(employee_id: EmpId, skill_id: int, conn: DbConn):
    """**Endpoint 2** — Why do we think this employee is proficient in this skill?"""
    return await svc.get_skill_evidence(conn, employee_id, skill_id)


@router.get("/{employee_id}/top-skills", response_model=EmployeeTopSkills)
async def get_top_skills(
    employee_id: EmpId,
    conn: DbConn,
    limit: int = Query(default=10, ge=1, le=50, description="Number of top skills to return"),
):
    """**Endpoint 8** — Skill passport: what are this employee's strongest skills?"""
    return await svc.get_top_skills(conn, employee_id, limit)


@router.get("/{employee_id}/evidence", response_model=EmployeeEvidenceInventory)
async def get_evidence_inventory(employee_id: EmpId, conn: DbConn):
    """**Endpoint 10** — All evidence items across all skills for this employee."""
    return await svc.get_evidence_inventory(conn, employee_id)
