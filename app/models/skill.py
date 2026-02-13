"""Skill-related Pydantic response models."""

from datetime import datetime

from pydantic import BaseModel

from app.models.common import EmployeeRef
from app.models.evidence import EvidenceItem


class SkillInfo(BaseModel):
    """Core skill metadata."""
    skill_id: int
    name: str
    category: str
    description: str | None = None


class EmployeeSkillEntry(BaseModel):
    """A single skill in an employee's profile."""
    skill_id: int
    skill_name: str
    category: str
    proficiency: int
    confidence: int
    source: str
    last_updated_at: datetime


# ── Endpoint 3: Top experts ───────────────────────────────────────────────────

class SkillExpert(BaseModel):
    employee_id: str
    display_name: str | None = None
    job_title: str | None = None
    org_name: str | None = None
    proficiency: int
    confidence: int
    last_updated_at: datetime


class TopExpertsResponse(BaseModel):
    skill: SkillInfo
    experts: list[SkillExpert]
    min_proficiency: int
    total_matching: int


# ── Endpoint 4: Skill coverage / distribution ─────────────────────────────────

class ProficiencyBucket(BaseModel):
    proficiency: int
    count: int


class SkillCoverageResponse(BaseModel):
    skill: SkillInfo
    total_employees: int
    employees_at_min: int
    min_proficiency: int
    distribution: list[ProficiencyBucket]


# ── Endpoint 6: Evidence-backed candidates ────────────────────────────────────

class EvidenceBackedCandidate(BaseModel):
    employee_id: str
    display_name: str | None = None
    job_title: str | None = None
    proficiency: int
    confidence: int
    top_evidence: list[EvidenceItem]


class EvidenceBackedResponse(BaseModel):
    skill: SkillInfo
    candidates: list[EvidenceBackedCandidate]
    min_proficiency: int
    min_evidence_strength: int


# ── Endpoint 7: Stale skills ─────────────────────────────────────────────────

class StaleSkillEntry(BaseModel):
    employee_id: str
    display_name: str | None = None
    job_title: str | None = None
    proficiency: int
    confidence: int
    last_updated_at: datetime
    days_since_update: int


class StaleSkillsResponse(BaseModel):
    skill: SkillInfo
    stale_entries: list[StaleSkillEntry]
    older_than_days: int
    total_stale: int


# ── Endpoint 9: Skill adjacency / co-occurrence ──────────────────────────────

class CooccurringSkill(BaseModel):
    skill_id: int
    skill_name: str
    category: str
    co_occurrence_count: int


class SkillAdjacencyResponse(BaseModel):
    skill: SkillInfo
    min_proficiency: int
    cooccurring: list[CooccurringSkill]


# ── Endpoint 11: Skill taxonomy ──────────────────────────────────────────────

class SkillCatalogResponse(BaseModel):
    skills: list[SkillInfo]
    total: int
