"""Org-centric response models (Endpoint 12)."""

from datetime import datetime

from pydantic import BaseModel


class OrgRef(BaseModel):
    org_id: str
    org_name: str
    business_unit: str | None = None


class OrgSkillSummaryEntry(BaseModel):
    skill_id: int
    name: str
    category: str
    employee_count: int
    avg_proficiency: float


class OrgSkillSummaryResponse(BaseModel):
    org: OrgRef
    includes_children: bool
    total_profiled_employees: int
    top_skills: list[OrgSkillSummaryEntry]


class OrgSkillExpert(BaseModel):
    employee_id: str
    display_name: str | None = None
    job_title: str | None = None
    org_name: str | None = None
    proficiency: int
    confidence: int
    last_updated_at: datetime


class OrgSkillExpertsResponse(BaseModel):
    org: OrgRef
    skill_id: int
    skill_name: str
    min_proficiency: int
    experts: list[OrgSkillExpert]
    total_matching: int
