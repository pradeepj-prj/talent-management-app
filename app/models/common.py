"""Shared Pydantic response models."""

from pydantic import BaseModel


class EmployeeRef(BaseModel):
    """Lightweight employee reference included in many responses."""
    employee_id: str
    display_name: str | None = None
    job_title: str | None = None
    job_family: str | None = None
    org_name: str | None = None
    seniority_level: int | None = None
