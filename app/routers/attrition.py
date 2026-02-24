"""Attrition prediction routes."""

from typing import Annotated

from asyncpg import Connection
from fastapi import APIRouter, Depends, Path, Query

from app.database import get_connection
from app.models.attrition import (
    AttritionRiskListResponse,
    EmployeeAttritionRisk,
    OrgAttritionSummary,
    RiskLevel,
)
from app.services import attrition_service as svc

router = APIRouter(prefix="/tm/attrition", tags=["Attrition Prediction"])

DbConn = Annotated[Connection, Depends(get_connection)]
EmpId = Annotated[str, Path(pattern=r"^EMP\d{6}$", description="Employee ID (e.g. EMP000001)")]
OrgId = Annotated[str, Path(pattern=r"^ORG\d{1,4}[A-Z]?$", description="Org unit ID (e.g. ORG030, ORG031B)")]


@router.get("/employees/{employee_id}", response_model=EmployeeAttritionRisk)
async def get_employee_attrition_risk(employee_id: EmpId, conn: DbConn):
    """Predict attrition risk for a single employee with full factor breakdown."""
    return await svc.get_employee_attrition_risk(conn, employee_id)


@router.get("/employees", response_model=AttritionRiskListResponse)
async def get_all_attrition_risks(
    conn: DbConn,
    limit: float = Query(default=50, ge=1, le=200, description="Page size"),
    offset: float = Query(default=0, ge=0, description="Offset for pagination"),
    min_risk: RiskLevel | None = Query(default=None, description="Minimum risk level filter"),
    sort: str = Query(default="risk_desc", pattern=r"^(risk_desc|risk_asc|name)$", description="Sort order"),
):
    """Paginated list of attrition predictions, sortable and filterable by risk level."""
    return await svc.get_all_attrition_risks(conn, int(limit), int(offset), min_risk, sort)


@router.get("/high-risk", response_model=AttritionRiskListResponse)
async def get_high_risk_employees(
    conn: DbConn,
    threshold: float = Query(default=0.25, ge=0.0, le=1.0, description="Minimum probability threshold"),
    limit: float = Query(default=50, ge=1, le=200, description="Page size"),
    offset: float = Query(default=0, ge=0, description="Offset for pagination"),
):
    """Employees above a probability threshold, sorted by risk descending."""
    return await svc.get_high_risk_employees(conn, float(threshold), int(limit), int(offset))


@router.get("/orgs/{org_unit_id}/summary", response_model=OrgAttritionSummary)
async def get_org_attrition_summary(
    org_unit_id: OrgId,
    conn: DbConn,
    top_risk_limit: float = Query(default=5, ge=1, le=20, description="Number of top risk employees to include"),
):
    """Org-level attrition summary with risk distribution and top-N riskiest employees."""
    return await svc.get_org_attrition_summary(conn, org_unit_id, int(top_risk_limit))
