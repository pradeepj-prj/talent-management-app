"""Evidence-related Pydantic response models."""

from datetime import date, datetime

from pydantic import BaseModel


class EvidenceItem(BaseModel):
    """A single evidence item backing a skill claim."""
    evidence_id: int
    evidence_type: str
    title: str
    issuer_or_system: str | None = None
    evidence_date: date | None = None
    url_or_ref: str | None = None
    signal_strength: int
    notes: str | None = None
    created_at: datetime


class EvidenceWithSkill(EvidenceItem):
    """Evidence item enriched with its associated skill info."""
    skill_id: int
    skill_name: str
