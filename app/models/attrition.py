"""Attrition prediction response models."""

from enum import Enum

from pydantic import BaseModel

from app.models.common import EmployeeRef


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AttritionFactor(BaseModel):
    """Single factor in the attrition prediction breakdown."""
    factor: str
    value: str
    multiplier: float
    description: str


class EmployeeAttritionRisk(BaseModel):
    """Attrition prediction for a single employee."""
    employee: EmployeeRef
    probability: float
    risk_level: RiskLevel
    factors: list[AttritionFactor]


class AttritionRiskListResponse(BaseModel):
    """Paginated list of employee attrition predictions."""
    employees: list[EmployeeAttritionRisk]
    total: int
    limit: int
    offset: int


class RiskDistribution(BaseModel):
    """Counts by risk level."""
    low: int = 0
    medium: int = 0
    high: int = 0
    critical: int = 0


class OrgAttritionSummary(BaseModel):
    """Org-level attrition summary with risk distribution."""
    org_id: str
    org_name: str
    total_employees: int
    avg_probability: float
    risk_distribution: RiskDistribution
    top_risk: list[EmployeeAttritionRisk]
