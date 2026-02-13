"""SQL queries for skill-centric endpoints (3, 4, 6, 7, 9, 11)."""

# ── Shared: fetch skill metadata ─────────────────────────────────────────────

GET_SKILL_INFO = """
    SELECT skill_id, name, category, description
    FROM skill
    WHERE skill_id = $1 AND is_active = TRUE
"""

# ── Endpoint 3: Top experts for a skill ──────────────────────────────────────

GET_TOP_EXPERTS = """
    SELECT es.employee_id, er.display_name, er.job_title, er.org_name,
           es.proficiency, es.confidence, es.last_updated_at
    FROM employee_skill es
    JOIN employee_ref er ON er.employee_id = es.employee_id
    WHERE es.skill_id = $1 AND es.proficiency >= $2
    ORDER BY es.proficiency DESC, es.confidence DESC, es.last_updated_at DESC
    LIMIT $3
"""

COUNT_EXPERTS = """
    SELECT count(*) FROM employee_skill
    WHERE skill_id = $1 AND proficiency >= $2
"""

# ── Endpoint 4: Skill coverage and distribution ─────────────────────────────

SKILL_DISTRIBUTION = """
    SELECT proficiency, count(*)::int AS count
    FROM employee_skill
    WHERE skill_id = $1
    GROUP BY proficiency
    ORDER BY proficiency
"""

SKILL_COVERAGE_COUNT = """
    SELECT count(*) FROM employee_skill
    WHERE skill_id = $1 AND proficiency >= $2
"""

SKILL_TOTAL_COUNT = """
    SELECT count(*) FROM employee_skill
    WHERE skill_id = $1
"""

# ── Endpoint 6: Evidence-backed candidates ───────────────────────────────────

GET_EVIDENCE_BACKED_CANDIDATES = """
    SELECT DISTINCT ON (es.employee_id)
           es.employee_id, er.display_name, er.job_title,
           es.proficiency, es.confidence
    FROM employee_skill es
    JOIN employee_ref er ON er.employee_id = es.employee_id
    WHERE es.skill_id = $1
      AND es.proficiency >= $2
      AND EXISTS (
          SELECT 1 FROM skill_evidence se
          WHERE se.employee_id = es.employee_id
            AND se.skill_id = es.skill_id
            AND se.signal_strength >= $3
      )
    ORDER BY es.employee_id, es.proficiency DESC, es.confidence DESC
"""

GET_STRONG_EVIDENCE_FOR_EMPLOYEES = """
    SELECT se.employee_id, se.evidence_id, se.evidence_type, se.title,
           se.issuer_or_system, se.evidence_date, se.url_or_ref,
           se.signal_strength, se.notes, se.created_at
    FROM skill_evidence se
    WHERE se.skill_id = $1
      AND se.signal_strength >= $2
      AND se.employee_id = ANY($3)
    ORDER BY se.employee_id, se.signal_strength DESC, se.evidence_date DESC NULLS LAST
"""

# ── Endpoint 7: Stale skills ────────────────────────────────────────────────

GET_STALE_SKILLS = """
    SELECT es.employee_id, er.display_name, er.job_title,
           es.proficiency, es.confidence, es.last_updated_at,
           EXTRACT(DAY FROM now() - es.last_updated_at)::int AS days_since_update
    FROM employee_skill es
    JOIN employee_ref er ON er.employee_id = es.employee_id
    WHERE es.skill_id = $1 AND es.last_updated_at < $2
    ORDER BY es.last_updated_at ASC
"""

# ── Endpoint 9: Skill adjacency / co-occurrence ─────────────────────────────

GET_COOCCURRING_SKILLS = """
    SELECT s2.skill_id, s2.name AS skill_name, s2.category,
           count(*)::int AS co_occurrence_count
    FROM employee_skill es1
    JOIN employee_skill es2
         ON es1.employee_id = es2.employee_id AND es1.skill_id != es2.skill_id
    JOIN skill s2 ON s2.skill_id = es2.skill_id
    WHERE es1.skill_id = $1 AND es1.proficiency >= $2
    GROUP BY s2.skill_id, s2.name, s2.category
    ORDER BY co_occurrence_count DESC
    LIMIT $3
"""

# ── Endpoint 11: Skill taxonomy browsing ─────────────────────────────────────

BROWSE_SKILLS = """
    SELECT skill_id, name, category, description
    FROM skill
    WHERE is_active = TRUE
      AND ($1::text IS NULL OR category::text = $1)
      AND ($2::text IS NULL OR name ILIKE '%' || $2 || '%' OR description ILIKE '%' || $2 || '%')
    ORDER BY category, name
"""
