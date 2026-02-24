"""SQL queries for employee-centric endpoints (1, 2, 8, 10)."""

# ── Name search ──────────────────────────────────────────────────────────────

SEARCH_EMPLOYEES_BY_NAME = """
    SELECT employee_id, display_name, job_title, job_family, org_name, seniority_level
    FROM employee_ref
    WHERE display_name ILIKE '%' || $1 || '%'
    ORDER BY display_name
    LIMIT $2
"""

COUNT_EMPLOYEES_BY_NAME = """
    SELECT count(*) FROM employee_ref
    WHERE display_name ILIKE '%' || $1 || '%'
"""

# ── Shared: fetch employee_ref row ────────────────────────────────────────────

GET_EMPLOYEE_REF = """
    SELECT employee_id, display_name, job_title, job_family, org_name, seniority_level
    FROM employee_ref
    WHERE employee_id = $1
"""

# ── Endpoint 1: Employee skill profile ────────────────────────────────────────

GET_EMPLOYEE_SKILLS = """
    SELECT s.skill_id, s.name AS skill_name, s.category,
           es.proficiency, es.confidence, es.source, es.last_updated_at
    FROM employee_skill es
    JOIN skill s ON s.skill_id = es.skill_id
    WHERE es.employee_id = $1
    ORDER BY es.proficiency DESC, es.confidence DESC, s.name
"""

# ── Endpoint 2: Evidence for a specific employee + skill ──────────────────────

GET_SKILL_CONTEXT = """
    SELECT s.name AS skill_name, es.proficiency, es.confidence
    FROM employee_skill es
    JOIN skill s ON s.skill_id = es.skill_id
    WHERE es.employee_id = $1 AND es.skill_id = $2
"""

GET_SKILL_EVIDENCE = """
    SELECT evidence_id, evidence_type, title, issuer_or_system,
           evidence_date, url_or_ref, signal_strength, notes, created_at
    FROM skill_evidence
    WHERE employee_id = $1 AND skill_id = $2
    ORDER BY signal_strength DESC, evidence_date DESC NULLS LAST
"""

# ── Endpoint 8: Top skills (skill passport) ──────────────────────────────────

GET_TOP_SKILLS = """
    SELECT s.skill_id, s.name AS skill_name, s.category,
           es.proficiency, es.confidence, es.source, es.last_updated_at
    FROM employee_skill es
    JOIN skill s ON s.skill_id = es.skill_id
    WHERE es.employee_id = $1
    ORDER BY es.proficiency DESC, es.confidence DESC, es.last_updated_at DESC
    LIMIT $2
"""

# ── Endpoint 10: Evidence inventory (all skills) ─────────────────────────────

GET_ALL_EVIDENCE = """
    SELECT se.evidence_id, se.evidence_type, se.title, se.issuer_or_system,
           se.evidence_date, se.url_or_ref, se.signal_strength, se.notes, se.created_at,
           se.skill_id, s.name AS skill_name
    FROM skill_evidence se
    JOIN skill s ON s.skill_id = se.skill_id
    WHERE se.employee_id = $1
    ORDER BY se.evidence_date DESC NULLS LAST, se.signal_strength DESC
"""
