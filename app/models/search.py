"""Multi-skill talent search response models (Endpoint 5)."""

from datetime import datetime

from pydantic import BaseModel


class MatchedSkill(BaseModel):
    skill_id: int
    skill_name: str
    proficiency: int
    confidence: int
    source: str
    last_updated_at: datetime


class TalentSearchHit(BaseModel):
    employee_id: str
    display_name: str | None = None
    job_title: str | None = None
    org_name: str | None = None
    seniority_level: int | None = None
    matched_skills: list[MatchedSkill]


class TalentSearchQuery(BaseModel):
    skill_names: list[str]
    min_proficiency: int
    results_count: int


class TalentSearchResponse(BaseModel):
    query: TalentSearchQuery
    results: list[TalentSearchHit]
