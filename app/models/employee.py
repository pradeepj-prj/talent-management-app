"""Employee-centric Pydantic response models."""

from pydantic import BaseModel

from app.models.common import EmployeeRef
from app.models.evidence import EvidenceItem, EvidenceWithSkill
from app.models.skill import EmployeeSkillEntry


class EmployeeSkillProfile(BaseModel):
    """Endpoint 1: Full skill profile for an employee."""
    employee: EmployeeRef
    skills: list[EmployeeSkillEntry]
    total_skills: int


class SkillEvidenceResponse(BaseModel):
    """Endpoint 2: Evidence behind a specific employee skill."""
    employee: EmployeeRef
    skill_id: int
    skill_name: str
    proficiency: int
    confidence: int
    evidence: list[EvidenceItem]


class EmployeeTopSkills(BaseModel):
    """Endpoint 8: Skill passport — top N skills."""
    employee: EmployeeRef
    skills: list[EmployeeSkillEntry]
    limit: int


class EmployeeEvidenceInventory(BaseModel):
    """Endpoint 10: All evidence across all skills."""
    employee: EmployeeRef
    evidence: list[EvidenceWithSkill]
    total_items: int


class EmployeeSearchResult(BaseModel):
    """Name search results."""
    employees: list[EmployeeRef]
    total: int
