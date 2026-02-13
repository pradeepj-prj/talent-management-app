"""SQL queries for multi-skill talent search (Endpoint 5)."""

# Resolve skill names to IDs
RESOLVE_SKILL_NAMES = """
    SELECT skill_id, name FROM skill
    WHERE name ILIKE ANY($1) AND is_active = TRUE
"""

# Find employees who have ALL specified skills at min_proficiency
# Uses relational division: GROUP BY + HAVING COUNT = number of skills
MULTI_SKILL_SEARCH = """
    SELECT es.employee_id, er.display_name, er.job_title, er.org_name, er.seniority_level
    FROM employee_skill es
    JOIN employee_ref er ON er.employee_id = es.employee_id
    WHERE es.skill_id = ANY($1)
      AND es.proficiency >= $2
    GROUP BY es.employee_id, er.display_name, er.job_title, er.org_name, er.seniority_level
    HAVING count(DISTINCT es.skill_id) = $3
    ORDER BY min(es.proficiency) DESC, er.display_name
"""

# Get per-skill details for matched employees
MATCHED_SKILL_DETAILS = """
    SELECT es.employee_id, es.skill_id, s.name AS skill_name,
           es.proficiency, es.confidence, es.source, es.last_updated_at
    FROM employee_skill es
    JOIN skill s ON s.skill_id = es.skill_id
    WHERE es.employee_id = ANY($1)
      AND es.skill_id = ANY($2)
    ORDER BY es.employee_id, es.proficiency DESC
"""
