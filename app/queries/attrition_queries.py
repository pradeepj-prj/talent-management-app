"""SQL queries for attrition prediction feature extraction.

These queries join across tm.* and public.* schemas to extract the 9 factors
used by the deterministic attrition model.  public.* tables must be explicitly
prefixed because the connection search_path is (tm, public) — unqualified names
resolve to tm first.
"""

# ── Active employee IDs in the TM system ─────────────────────────────────────

GET_ALL_ACTIVE_EMPLOYEE_IDS = """
    SELECT employee_id
    FROM employee_ref
    WHERE status = 'active'
    ORDER BY employee_id
"""

# ── Org tree → employee IDs (reuses existing recursive CTE pattern) ──────────

GET_ORG_EMPLOYEE_IDS = """
    WITH RECURSIVE org_tree AS (
        SELECT org_id FROM org_unit_ref WHERE org_id = $1
        UNION ALL
        SELECT o.org_id FROM org_unit_ref o JOIN org_tree t ON o.parent_org_id = t.org_id
    )
    SELECT er.employee_id
    FROM org_tree ot
    JOIN employee_ref er ON er.org_id = ot.org_id
    WHERE er.status = 'active'
    ORDER BY er.employee_id
"""

# ── Feature extraction for a single employee ─────────────────────────────────
#
# Returns one row with all raw feature values needed by the attrition model.
# CTE breakdown:
#   latest_perf     – most recent performance rating from public.employee_performance
#   promotion_check – whether the employee had a job change in the last 18 months
#   skill_stats     – avg days since skill update + skill count
#   leadership_check – has a leadership-category skill at proficiency >= 3
#   evidence_recent – count of evidence items dated within the last 12 months

GET_EMPLOYEE_FEATURES = """
    WITH latest_perf AS (
        SELECT ep.rating
        FROM public.employee_performance ep
        WHERE ep.employee_id = $1
        ORDER BY ep.review_period_year DESC, ep.review_date DESC
        LIMIT 1
    ),
    promotion_check AS (
        SELECT CASE WHEN count(*) > 0 THEN true ELSE false END AS promoted_recently
        FROM public.employee_job_assignment ja
        WHERE ja.employee_id = $1
          AND ja.start_date > current_date - interval '18 months'
          AND ja.start_date != (
              SELECT min(ja2.start_date)
              FROM public.employee_job_assignment ja2
              WHERE ja2.employee_id = $1
          )
    ),
    skill_stats AS (
        SELECT coalesce(avg(extract(epoch FROM (now() - es.last_updated_at)) / 86400), 0)::float AS avg_days_since_update,
               count(*)::int AS skill_count
        FROM employee_skill es
        WHERE es.employee_id = $1
    ),
    leadership_check AS (
        SELECT CASE WHEN count(*) > 0 THEN true ELSE false END AS has_leadership
        FROM employee_skill es
        JOIN skill s ON s.skill_id = es.skill_id
        WHERE es.employee_id = $1
          AND s.category = 'leadership'
          AND es.proficiency >= 3
    ),
    evidence_recent AS (
        SELECT count(*)::int AS recent_evidence_count
        FROM skill_evidence se
        WHERE se.employee_id = $1
          AND se.evidence_date > current_date - interval '12 months'
    )
    SELECT er.employee_id, er.display_name, er.job_title, er.job_family,
           er.org_name, er.seniority_level,
           e.hire_date, e.employment_type,
           lp.rating AS latest_rating,
           pc.promoted_recently,
           ss.avg_days_since_update, ss.skill_count,
           lc.has_leadership,
           ev.recent_evidence_count
    FROM employee_ref er
    JOIN public.employee e ON e.employee_id = er.employee_id
    LEFT JOIN latest_perf lp ON true
    LEFT JOIN promotion_check pc ON true
    LEFT JOIN skill_stats ss ON true
    LEFT JOIN leadership_check lc ON true
    LEFT JOIN evidence_recent ev ON true
    WHERE er.employee_id = $1
      AND er.status = 'active'
"""

# ── Batch feature extraction (array of employee IDs) ─────────────────────────
#
# Same logic as GET_EMPLOYEE_FEATURES but uses LATERAL joins to process
# multiple employees in a single query.  $1 is a TEXT[] array parameter.

GET_EMPLOYEE_FEATURES_BATCH = """
    SELECT er.employee_id, er.display_name, er.job_title, er.job_family,
           er.org_name, er.seniority_level,
           e.hire_date, e.employment_type,
           lp.rating AS latest_rating,
           pc.promoted_recently,
           ss.avg_days_since_update, ss.skill_count,
           lc.has_leadership,
           ev.recent_evidence_count
    FROM employee_ref er
    JOIN public.employee e ON e.employee_id = er.employee_id
    LEFT JOIN LATERAL (
        SELECT ep.rating
        FROM public.employee_performance ep
        WHERE ep.employee_id = er.employee_id
        ORDER BY ep.review_period_year DESC, ep.review_date DESC
        LIMIT 1
    ) lp ON true
    LEFT JOIN LATERAL (
        SELECT CASE WHEN count(*) > 0 THEN true ELSE false END AS promoted_recently
        FROM public.employee_job_assignment ja
        WHERE ja.employee_id = er.employee_id
          AND ja.start_date > current_date - interval '18 months'
          AND ja.start_date != (
              SELECT min(ja2.start_date)
              FROM public.employee_job_assignment ja2
              WHERE ja2.employee_id = er.employee_id
          )
    ) pc ON true
    LEFT JOIN LATERAL (
        SELECT coalesce(avg(extract(epoch FROM (now() - es.last_updated_at)) / 86400), 0)::float AS avg_days_since_update,
               count(*)::int AS skill_count
        FROM employee_skill es
        WHERE es.employee_id = er.employee_id
    ) ss ON true
    LEFT JOIN LATERAL (
        SELECT CASE WHEN count(*) > 0 THEN true ELSE false END AS has_leadership
        FROM employee_skill es
        JOIN skill s ON s.skill_id = es.skill_id
        WHERE es.employee_id = er.employee_id
          AND s.category = 'leadership'
          AND es.proficiency >= 3
    ) lc ON true
    LEFT JOIN LATERAL (
        SELECT count(*)::int AS recent_evidence_count
        FROM skill_evidence se
        WHERE se.employee_id = er.employee_id
          AND se.evidence_date > current_date - interval '12 months'
    ) ev ON true
    WHERE er.employee_id = ANY($1)
      AND er.status = 'active'
    ORDER BY er.employee_id
"""
