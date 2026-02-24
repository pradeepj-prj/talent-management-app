"""Business logic for attrition prediction endpoints.

Deterministic rules-based model:
  P(leave) = 0.12 × perf × tenure × emp_type × seniority × promotion
             × skill_staleness × skill_breadth × leadership × evidence_currency
  (capped at 0.95)

Each factor returns a multiplier and a human-readable explanation, making
the prediction fully explainable.
"""

from datetime import date, timedelta

from asyncpg import Connection, Record
from fastapi import HTTPException

from app.models.attrition import (
    AttritionFactor,
    AttritionRiskListResponse,
    EmployeeAttritionRisk,
    OrgAttritionSummary,
    RiskDistribution,
    RiskLevel,
)
from app.models.common import EmployeeRef
from app.queries import attrition_queries as Q
from app.queries import org_queries as OQ

BASE_RATE = 0.12
MAX_PROBABILITY = 0.95


# ── Factor multiplier functions ──────────────────────────────────────────────
# Each returns (multiplier, raw_value_str, description).

def _performance_factor(rating: int | None) -> tuple[float, str, str]:
    mapping = {1: 2.5, 2: 1.5, 3: 1.0, 4: 0.7, 5: 0.4}
    if rating is None:
        return 1.0, "N/A", "No performance rating on record"
    mult = mapping.get(rating, 1.0)
    labels = {1: "Does Not Meet", 2: "Partially Meets", 3: "Meets",
              4: "Exceeds", 5: "Outstanding"}
    label = labels.get(rating, f"Rating {rating}")
    if mult > 1.0:
        desc = f"Low rating ({label}) increases flight risk"
    elif mult < 1.0:
        desc = f"Strong rating ({label}) reduces flight risk"
    else:
        desc = f"Average rating ({label}) — baseline risk"
    return mult, str(rating), desc


def _tenure_factor(hire_date: date | None) -> tuple[float, str, str]:
    if hire_date is None:
        return 1.0, "N/A", "Hire date not available"
    years = (date.today() - hire_date).days / 365.25
    if years < 1:
        mult, band = 1.8, "<1 year"
    elif years < 2:
        mult, band = 1.2, "1-2 years"
    elif years < 5:
        mult, band = 1.0, "2-5 years"
    elif years < 10:
        mult, band = 0.7, "5-10 years"
    else:
        mult, band = 0.5, "10+ years"
    desc = (f"Tenure {band} ({years:.1f}y) — "
            + ("short tenure increases risk" if mult > 1.0
               else "long tenure reduces risk" if mult < 1.0
               else "baseline risk"))
    return mult, f"{years:.1f} years", desc


def _employment_type_factor(emp_type: str | None) -> tuple[float, str, str]:
    mapping = {"Full-time": 1.0, "Contract": 2.0, "Part-time": 1.4}
    if emp_type is None:
        return 1.0, "N/A", "Employment type not available"
    mult = mapping.get(emp_type, 1.0)
    if mult > 1.0:
        desc = f"{emp_type} employment has higher turnover"
    else:
        desc = f"{emp_type} employment — baseline risk"
    return mult, emp_type, desc


def _seniority_factor(level: int | None) -> tuple[float, str, str]:
    mapping = {1: 1.3, 2: 1.1, 3: 0.9, 4: 0.7, 5: 0.5}
    if level is None:
        return 1.0, "N/A", "Seniority level not available"
    mult = mapping.get(level, 1.0)
    if mult > 1.0:
        desc = f"Junior level ({level}) has higher mobility"
    elif mult < 1.0:
        desc = f"Senior level ({level}) reduces flight risk"
    else:
        desc = f"Mid-level ({level}) — baseline risk"
    return mult, str(level), desc


def _promotion_factor(promoted: bool | None) -> tuple[float, str, str]:
    if promoted is None:
        return 1.0, "N/A", "Promotion data not available"
    if promoted:
        return 0.4, "Yes", "Recent promotion (last 18 months) strongly reduces risk"
    return 1.0, "No", "No recent promotion — baseline risk"


def _skill_staleness_factor(avg_days: float | None) -> tuple[float, str, str]:
    if avg_days is None or avg_days == 0:
        return 1.0, "N/A", "No skill data available"
    if avg_days < 180:
        mult, band = 0.8, "<6 months"
    elif avg_days < 365:
        mult, band = 1.0, "6-12 months"
    elif avg_days < 730:
        mult, band = 1.3, "1-2 years"
    else:
        mult, band = 1.6, ">2 years"
    desc = (f"Avg skill update {band} ago ({avg_days:.0f}d) — "
            + ("fresh skills reduce risk" if mult < 1.0
               else "stale skills increase risk" if mult > 1.0
               else "baseline risk"))
    return mult, f"{avg_days:.0f} days", desc


def _skill_breadth_factor(count: int | None) -> tuple[float, str, str]:
    if count is None:
        count = 0
    if count <= 2:
        mult, band = 1.5, "0-2"
    elif count <= 5:
        mult, band = 1.2, "3-5"
    elif count <= 9:
        mult, band = 1.0, "6-9"
    elif count <= 14:
        mult, band = 0.9, "10-14"
    else:
        mult, band = 0.8, "15+"
    desc = (f"{count} skills ({band} range) — "
            + ("narrow skillset increases risk" if mult > 1.0
               else "broad skillset reduces risk" if mult < 1.0
               else "moderate breadth — baseline risk"))
    return mult, str(count), desc


def _leadership_factor(has_leadership: bool | None, seniority: int | None) -> tuple[float, str, str]:
    sen = seniority or 0
    if sen < 3:
        return 1.0, "N/A", "Below seniority 3 — leadership factor not applicable"
    if has_leadership:
        return 0.6, "Yes", "Leadership skills at senior level — invested in growth, lower risk"
    return 1.2, "No", "Senior employee without leadership skills — potential dissatisfaction"


def _evidence_currency_factor(recent_count: int | None) -> tuple[float, str, str]:
    if recent_count is None:
        recent_count = 0
    if recent_count >= 3:
        mult = 0.7
        desc = f"{recent_count} recent evidence items — actively developing, lower risk"
    elif recent_count >= 1:
        mult = 0.85
        desc = f"{recent_count} recent evidence item(s) — some development activity"
    else:
        mult = 1.2
        desc = "No recent evidence — possible disengagement increases risk"
    return mult, str(recent_count), desc


# ── Core prediction ──────────────────────────────────────────────────────────

def _classify_risk(probability: float) -> RiskLevel:
    if probability < 0.10:
        return RiskLevel.low
    if probability < 0.25:
        return RiskLevel.medium
    if probability < 0.50:
        return RiskLevel.high
    return RiskLevel.critical


def _compute_prediction(row: Record) -> EmployeeAttritionRisk:
    """Compute attrition prediction from a feature-extraction row."""
    factors: list[AttritionFactor] = []
    probability = BASE_RATE

    # 1. Performance
    mult, val, desc = _performance_factor(row["latest_rating"])
    probability *= mult
    factors.append(AttritionFactor(factor="Performance", value=val, multiplier=mult, description=desc))

    # 2. Tenure
    mult, val, desc = _tenure_factor(row["hire_date"])
    probability *= mult
    factors.append(AttritionFactor(factor="Tenure", value=val, multiplier=mult, description=desc))

    # 3. Employment type
    mult, val, desc = _employment_type_factor(row["employment_type"])
    probability *= mult
    factors.append(AttritionFactor(factor="Employment Type", value=val, multiplier=mult, description=desc))

    # 4. Seniority
    seniority = row["seniority_level"]
    mult, val, desc = _seniority_factor(seniority)
    probability *= mult
    factors.append(AttritionFactor(factor="Seniority", value=val, multiplier=mult, description=desc))

    # 5. Recent promotion
    mult, val, desc = _promotion_factor(row["promoted_recently"])
    probability *= mult
    factors.append(AttritionFactor(factor="Recent Promotion", value=val, multiplier=mult, description=desc))

    # 6. Skill staleness
    mult, val, desc = _skill_staleness_factor(row["avg_days_since_update"])
    probability *= mult
    factors.append(AttritionFactor(factor="Skill Staleness", value=val, multiplier=mult, description=desc))

    # 7. Skill breadth
    mult, val, desc = _skill_breadth_factor(row["skill_count"])
    probability *= mult
    factors.append(AttritionFactor(factor="Skill Breadth", value=val, multiplier=mult, description=desc))

    # 8. Leadership development
    mult, val, desc = _leadership_factor(row["has_leadership"], seniority)
    probability *= mult
    factors.append(AttritionFactor(factor="Leadership Development", value=val, multiplier=mult, description=desc))

    # 9. Evidence currency
    mult, val, desc = _evidence_currency_factor(row["recent_evidence_count"])
    probability *= mult
    factors.append(AttritionFactor(factor="Evidence Currency", value=val, multiplier=mult, description=desc))

    # Cap
    probability = min(probability, MAX_PROBABILITY)
    probability = round(probability, 4)

    employee = EmployeeRef(
        employee_id=row["employee_id"],
        display_name=row["display_name"],
        job_title=row["job_title"],
        job_family=row["job_family"],
        org_name=row["org_name"],
        seniority_level=seniority,
    )

    return EmployeeAttritionRisk(
        employee=employee,
        probability=probability,
        risk_level=_classify_risk(probability),
        factors=factors,
    )


# ── Service functions ────────────────────────────────────────────────────────

async def get_employee_attrition_risk(
    conn: Connection, employee_id: str,
) -> EmployeeAttritionRisk:
    """Single employee attrition prediction with full factor breakdown."""
    row = await conn.fetchrow(Q.GET_EMPLOYEE_FEATURES, employee_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found or not active in TM system")
    return _compute_prediction(row)


async def _fetch_and_predict_batch(
    conn: Connection, employee_ids: list[str],
) -> list[EmployeeAttritionRisk]:
    """Fetch features for a batch of employees and compute predictions."""
    if not employee_ids:
        return []
    rows = await conn.fetch(Q.GET_EMPLOYEE_FEATURES_BATCH, employee_ids)
    return [_compute_prediction(r) for r in rows]


async def get_all_attrition_risks(
    conn: Connection,
    limit: int = 50,
    offset: int = 0,
    min_risk: RiskLevel | None = None,
    sort_by: str = "risk_desc",
) -> AttritionRiskListResponse:
    """Paginated list of attrition predictions, sortable and filterable."""
    # Get all active employee IDs
    id_rows = await conn.fetch(Q.GET_ALL_ACTIVE_EMPLOYEE_IDS)
    all_ids = [r["employee_id"] for r in id_rows]

    # Fetch features in a single batch
    all_predictions = await _fetch_and_predict_batch(conn, all_ids)

    # Filter by minimum risk level
    if min_risk is not None:
        risk_order = {RiskLevel.low: 0, RiskLevel.medium: 1, RiskLevel.high: 2, RiskLevel.critical: 3}
        min_ord = risk_order[min_risk]
        all_predictions = [p for p in all_predictions if risk_order[p.risk_level] >= min_ord]

    # Sort
    if sort_by == "risk_desc":
        all_predictions.sort(key=lambda p: p.probability, reverse=True)
    elif sort_by == "risk_asc":
        all_predictions.sort(key=lambda p: p.probability)
    elif sort_by == "name":
        all_predictions.sort(key=lambda p: (p.employee.display_name or ""))

    total = len(all_predictions)
    page = all_predictions[offset:offset + limit]

    return AttritionRiskListResponse(employees=page, total=total, limit=limit, offset=offset)


async def get_high_risk_employees(
    conn: Connection,
    threshold: float = 0.25,
    limit: int = 50,
    offset: int = 0,
) -> AttritionRiskListResponse:
    """Employees above a probability threshold, sorted by risk descending."""
    id_rows = await conn.fetch(Q.GET_ALL_ACTIVE_EMPLOYEE_IDS)
    all_ids = [r["employee_id"] for r in id_rows]

    all_predictions = await _fetch_and_predict_batch(conn, all_ids)

    # Filter by threshold
    filtered = [p for p in all_predictions if p.probability >= threshold]
    filtered.sort(key=lambda p: p.probability, reverse=True)

    total = len(filtered)
    page = filtered[offset:offset + limit]

    return AttritionRiskListResponse(employees=page, total=total, limit=limit, offset=offset)


async def get_org_attrition_summary(
    conn: Connection, org_id: str, top_risk_limit: int = 5,
) -> OrgAttritionSummary:
    """Org-level attrition summary with risk distribution and top-N riskiest."""
    # Verify org exists
    org_row = await conn.fetchrow(OQ.GET_ORG_REF, org_id)
    if not org_row:
        raise HTTPException(status_code=404, detail=f"Org unit {org_id} not found")

    # Get employee IDs in org tree
    id_rows = await conn.fetch(Q.GET_ORG_EMPLOYEE_IDS, org_id)
    emp_ids = [r["employee_id"] for r in id_rows]

    if not emp_ids:
        return OrgAttritionSummary(
            org_id=org_row["org_id"],
            org_name=org_row["org_name"],
            total_employees=0,
            avg_probability=0.0,
            risk_distribution=RiskDistribution(),
            top_risk=[],
        )

    predictions = await _fetch_and_predict_batch(conn, emp_ids)

    # Risk distribution
    dist = RiskDistribution()
    total_prob = 0.0
    for p in predictions:
        total_prob += p.probability
        if p.risk_level == RiskLevel.low:
            dist.low += 1
        elif p.risk_level == RiskLevel.medium:
            dist.medium += 1
        elif p.risk_level == RiskLevel.high:
            dist.high += 1
        else:
            dist.critical += 1

    avg_prob = round(total_prob / len(predictions), 4) if predictions else 0.0

    # Top N riskiest
    predictions.sort(key=lambda p: p.probability, reverse=True)
    top_risk = predictions[:top_risk_limit]

    return OrgAttritionSummary(
        org_id=org_row["org_id"],
        org_name=org_row["org_name"],
        total_employees=len(predictions),
        avg_probability=avg_prob,
        risk_distribution=dist,
        top_risk=top_risk,
    )
