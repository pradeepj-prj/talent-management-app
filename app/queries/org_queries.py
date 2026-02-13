"""SQL queries for org-centric endpoints (Endpoint 12)."""

# Fetch org unit metadata
GET_ORG_REF = """
    SELECT org_id, org_name, business_unit
    FROM org_unit_ref
    WHERE org_id = $1
"""

# Recursive CTE: get org + all descendant org_ids
# Used by both sub-endpoints
ORG_TREE_CTE = """
    WITH RECURSIVE org_tree AS (
        SELECT org_id FROM org_unit_ref WHERE org_id = $1
        UNION ALL
        SELECT o.org_id FROM org_unit_ref o JOIN org_tree t ON o.parent_org_id = t.org_id
    )
"""

# Top skills across an org tree
ORG_SKILL_SUMMARY = ORG_TREE_CTE + """
    SELECT s.skill_id, s.name, s.category,
           count(DISTINCT es.employee_id)::int AS employee_count,
           round(avg(es.proficiency), 1)::float AS avg_proficiency
    FROM org_tree ot
    JOIN employee_ref er ON er.org_id = ot.org_id
    JOIN employee_skill es ON es.employee_id = er.employee_id
    JOIN skill s ON s.skill_id = es.skill_id
    GROUP BY s.skill_id, s.name, s.category
    ORDER BY employee_count DESC, avg_proficiency DESC
    LIMIT $2
"""

# Count profiled employees in org tree
ORG_EMPLOYEE_COUNT = ORG_TREE_CTE + """
    SELECT count(DISTINCT er.employee_id)::int
    FROM org_tree ot
    JOIN employee_ref er ON er.org_id = ot.org_id
"""

# Experts for a specific skill within an org tree
ORG_SKILL_EXPERTS = ORG_TREE_CTE + """
    SELECT es.employee_id, er.display_name, er.job_title, er.org_name,
           es.proficiency, es.confidence, es.last_updated_at
    FROM org_tree ot
    JOIN employee_ref er ON er.org_id = ot.org_id
    JOIN employee_skill es ON es.employee_id = er.employee_id
    WHERE es.skill_id = $2 AND es.proficiency >= $3
    ORDER BY es.proficiency DESC, es.confidence DESC
    LIMIT $4
"""

# Count matching experts for a skill in org tree
ORG_SKILL_EXPERT_COUNT = ORG_TREE_CTE + """
    SELECT count(*)::int
    FROM org_tree ot
    JOIN employee_ref er ON er.org_id = ot.org_id
    JOIN employee_skill es ON es.employee_id = er.employee_id
    WHERE es.skill_id = $2 AND es.proficiency >= $3
"""
