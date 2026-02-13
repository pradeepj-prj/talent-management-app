# Talent Management Skills API

A demo REST API that answers **12 business questions** about employee skills, proficiency, evidence, and talent search. Built as a playground mimicking enterprise Talent Management platforms (like entomo's Competency/Skill Management module).

The API runs on top of an HR employee database ([HR-Data-Generator](https://github.com/pradeepj-prj/HR-Data-Generator)), with a dedicated `tm` schema for skill data — mirroring how real enterprises keep HR master data separate from talent management systems.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL (hr_data)                      │
│                                                             │
│  ┌──────────────────┐         ┌───────────────────────────┐ │
│  │  public schema   │         │       tm schema           │ │
│  │  (HR tables)     │  sync   │  org_unit_ref             │ │
│  │  ─────────────   │ ──────► │  employee_ref (enriched)  │ │
│  │  employee        │         │  skill (93 skills)        │ │
│  │  employee_job_*  │         │  employee_skill (13,410)  │ │
│  │  employee_org_*  │         │  skill_evidence (18,794)  │ │
│  │  organization_*  │         └───────────────────────────┘ │
│  └──────────────────┘                    ▲                  │
└──────────────────────────────────────────│──────────────────┘
                                           │ asyncpg
                                  ┌────────┴────────┐
                                  │   FastAPI App    │
                                  │  14 endpoints    │
                                  │  4 tag groups    │
                                  └─────────────────┘
```

**Key design decisions:**

- **Schema separation** — The `tm` schema lives inside the `hr_data` database but is logically independent. The `employee_ref` table is a local sync of HR master data so the API is self-contained at runtime (no cross-schema joins needed).
- **asyncpg** — Native async PostgreSQL driver for true non-blocking I/O with FastAPI. Queries use `$1, $2` positional parameters (prepared statements), not ORM-generated SQL.
- **Raw SQL** — All queries are hand-written in dedicated `queries/` modules. This gives full control over PostgreSQL features like recursive CTEs, window functions, and `HAVING` clauses that ORMs often abstract poorly.

---

## Quick Start

### Prerequisites

- Python 3.10+
- Access to the PostgreSQL server with the HR database (see [HR-Data-Generator](https://github.com/pradeepj-prj/HR-Data-Generator))

### 1. Install dependencies

```bash
pip install -e ".[dev,generator]"
```

The `dev` extra includes pytest/httpx for testing. The `generator` extra includes psycopg2 for the data generation script.

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your database credentials
```

### 3. Create the schema

Run the schema DDL against your PostgreSQL database:

```bash
# Using psql:
psql -h <host> -U <user> -d hr_data -f tm_schema.sql

# Or using the Python approach (if psql is unavailable):
python -c "
import psycopg2
conn = psycopg2.connect(host='...', database='hr_data', user='...', password='...')
conn.autocommit = False
with open('tm_schema.sql') as f:
    conn.cursor().execute(f.read())
conn.commit()
"
```

### 4. Generate skill data

```bash
python scripts/generate_tm_data.py --seed 42 --sample-pct 70
```

This reads active employees from the HR database and generates:
- 93 skills across 5 categories (technical, functional, leadership, domain, tool)
- Skill assignments for ~70% of active employees
- Evidence items (certifications, projects, assessments, manager reviews, peer endorsements)
- ~17% staleness injection (skills not updated in >1 year)

The `--seed` flag ensures reproducible output. Use `--sample-pct` to control what percentage of employees get skill profiles.

### 5. Start the API

```bash
uvicorn app.main:app --reload
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive Swagger UI.

### 6. Run tests

```bash
pytest tests/ -v
```

All 48 integration tests run against the real database with generated data.

---

## API Endpoints

All endpoints are prefixed with `/tm` and organized into 4 groups.

### Employees (Endpoints 1, 2, 8, 10)

| # | Method | Path | Description |
|---|--------|------|-------------|
| 1 | GET | `/tm/employees/{employee_id}/skills` | Full skill profile with proficiency, confidence, and source |
| 2 | GET | `/tm/employees/{employee_id}/skills/{skill_id}/evidence` | Evidence items backing a specific skill claim |
| 8 | GET | `/tm/employees/{employee_id}/top-skills?limit=10` | Skill passport — top N skills ranked by proficiency |
| 10 | GET | `/tm/employees/{employee_id}/evidence` | All evidence items across all skills |

### Skills (Endpoints 3, 4, 6, 7, 9, 11)

| # | Method | Path | Description |
|---|--------|------|-------------|
| 11 | GET | `/tm/skills?category=technical&search=python` | Browse skill catalog with optional filters |
| 3 | GET | `/tm/skills/{skill_id}/experts?min_proficiency=4&limit=20` | Top experts ranked by proficiency and confidence |
| 4 | GET | `/tm/skills/{skill_id}/coverage?min_proficiency=3` | Employee count + proficiency distribution histogram (levels 0–5) |
| 6 | GET | `/tm/skills/{skill_id}/candidates?min_proficiency=3&min_evidence_strength=4` | Employees with skill AND strong evidence to back it up |
| 7 | GET | `/tm/skills/{skill_id}/stale?older_than_days=365` | Skills not validated recently — governance/freshness check |
| 9 | GET | `/tm/skills/{skill_id}/cooccurring?min_proficiency=3&top=20` | Skills that commonly co-occur (adjacency analysis) |

### Talent Search (Endpoint 5)

| # | Method | Path | Description |
|---|--------|------|-------------|
| 5 | GET | `/tm/talent/search?skills=Python,SQL&min_proficiency=3` | Multi-skill AND search — find employees with ALL specified skills |

### Organizations (Endpoint 12)

| # | Method | Path | Description |
|---|--------|------|-------------|
| 12a | GET | `/tm/orgs/{org_unit_id}/skills/summary?limit=20` | Top skills across an org unit (includes child orgs via recursive CTE) |
| 12b | GET | `/tm/orgs/{org_unit_id}/skills/{skill_id}/experts?min_proficiency=3` | Experts for a skill within an org unit |

---

## Example API Calls

```bash
# Health check
curl http://localhost:8000/health

# Employee skill profile
curl http://localhost:8000/tm/employees/EMP000001/skills

# Top 5 Python experts
curl "http://localhost:8000/tm/skills/1/experts?min_proficiency=4&limit=5"

# Python proficiency distribution
curl "http://localhost:8000/tm/skills/1/coverage?min_proficiency=3"

# Stale Python skills (not updated in 1 year)
curl "http://localhost:8000/tm/skills/1/stale?older_than_days=365"

# What skills co-occur with Python?
curl "http://localhost:8000/tm/skills/1/cooccurring?min_proficiency=3&top=10"

# Find employees with both Python AND SQL at proficiency >= 4
curl "http://localhost:8000/tm/talent/search?skills=Python,SQL&min_proficiency=4"

# Engineering org skill summary (includes all child orgs)
curl "http://localhost:8000/tm/orgs/ORG030/skills/summary?limit=10"

# Browse leadership skills
curl "http://localhost:8000/tm/skills?category=leadership"
```

---

## Project Structure

```
tm_app/
├── CLAUDE.md                          # Project instructions for Claude Code
├── README.md                          # This file
├── tm_schema.sql                      # PostgreSQL DDL for the tm schema
├── tm_business_questions.md           # 12 business questions specification
├── pyproject.toml                     # Dependencies and project metadata
├── .env.example                       # Environment template
├── .gitignore
│
├── scripts/
│   └── generate_tm_data.py            # Reads HR DB → writes TM skill data
│
├── app/
│   ├── main.py                        # FastAPI app, lifespan, CORS, exception handler
│   ├── config.py                      # pydantic-settings (DB connection)
│   ├── database.py                    # asyncpg pool + FastAPI dependency
│   │
│   ├── models/                        # Pydantic response schemas
│   │   ├── common.py                  #   EmployeeRef (shared)
│   │   ├── employee.py                #   Endpoints 1, 2, 8, 10
│   │   ├── skill.py                   #   Endpoints 3, 4, 6, 7, 9, 11
│   │   ├── evidence.py                #   Evidence items
│   │   ├── search.py                  #   Endpoint 5
│   │   └── org.py                     #   Endpoint 12
│   │
│   ├── queries/                       # Raw SQL (asyncpg $1 params)
│   │   ├── employee_queries.py        #   Endpoints 1, 2, 8, 10
│   │   ├── skill_queries.py           #   Endpoints 3, 4, 6, 7, 9, 11
│   │   ├── search_queries.py          #   Endpoint 5
│   │   └── org_queries.py             #   Endpoint 12 (recursive CTE)
│   │
│   ├── services/                      # Business logic layer
│   │   ├── employee_service.py
│   │   ├── skill_service.py
│   │   ├── search_service.py
│   │   └── org_service.py
│   │
│   └── routers/                       # FastAPI route handlers
│       ├── employees.py               #   /tm/employees/...
│       ├── skills.py                  #   /tm/skills/...
│       ├── talent_search.py           #   /tm/talent/search
│       └── orgs.py                    #   /tm/orgs/...
│
└── tests/                             # 48 integration tests
    ├── conftest.py                    #   Session-scoped DB pool fixture
    ├── test_health.py
    ├── test_employees.py
    ├── test_skills.py
    ├── test_search.py
    └── test_orgs.py
```

---

## Database Schema

The `tm` schema contains 5 tables:

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `org_unit_ref` | HR org hierarchy (synced) | `org_id`, `parent_org_id`, `org_name` |
| `employee_ref` | HR employee snapshot (enriched) | `employee_id`, `display_name`, `job_title`, `org_id`, `seniority_level` |
| `skill` | Skill catalog (93 skills) | `skill_id`, `name`, `category`, `is_active` |
| `employee_skill` | Employee ↔ Skill assignments | `employee_id`, `skill_id`, `proficiency` (0–5), `confidence` (0–100) |
| `skill_evidence` | Evidence backing skill claims | `evidence_id`, `evidence_type`, `signal_strength` (1–5) |

**Enums:** `skill_category`, `skill_source`, `evidence_type`

### Skill categories

| Category | Count | Examples |
|----------|-------|---------|
| technical | 31 | Python, PCB Design, Six Sigma, Root Cause Analysis |
| tool | 25 | Docker, Kubernetes, Salesforce CRM, SAP FICO |
| functional | 25 | Pipeline Management, HR Analytics, Communication |
| leadership | 8 | People Management, Strategic Planning, Coaching |
| domain | 4 | ISO 9001, IATF 16949, CAPA, ITIL |

---

## Data Generation

The `scripts/generate_tm_data.py` script creates realistic skill data by:

1. **Reading HR data** — Active employees with current job and org assignments
2. **Sampling** — Selecting ~70% (configurable) of employees for skill profiling
3. **Job-group matching** — Software engineers get Python/Docker, sales gets Salesforce/Pipeline Management, etc.
4. **Seniority correlation** — Senior employees get more skills (4–20 range), higher proficiency, and leadership skills (seniority 3+)
5. **Evidence generation** — Certifications (AWS, Coursera), projects, assessments (HackerRank), manager reviews, peer endorsements
6. **Staleness injection** — ~17% of skills have `last_updated_at` older than 1 year (for endpoint 7)
7. **Seeded randomness** — `--seed 42` for reproducible output

### Generated data (seed=42, 70% sample)

| Metric | Value |
|--------|-------|
| Employees profiled | 1,348 / 1,927 active |
| Skills in catalog | 93 |
| Skill assignments | 13,410 (avg 9.9/employee) |
| Evidence items | 18,794 (avg 1.4/skill) |
| Stale skills (>1yr) | 2,253 (16.8%) |

---

## Notable Query Patterns

### Relational Division (Endpoint 5)

The multi-skill AND search finds employees who have **all** specified skills — a classic "relational division" problem:

```sql
SELECT es.employee_id, ...
FROM employee_skill es
WHERE es.skill_id = ANY($1) AND es.proficiency >= $2
GROUP BY es.employee_id
HAVING count(DISTINCT es.skill_id) = $3  -- must match ALL skills
```

### Recursive CTE (Endpoint 12)

Org hierarchy traversal walks the `parent_org_id` chain so a query for "Engineering" includes all sub-departments:

```sql
WITH RECURSIVE org_tree AS (
    SELECT org_id FROM org_unit_ref WHERE org_id = $1
    UNION ALL
    SELECT o.org_id FROM org_unit_ref o
    JOIN org_tree t ON o.parent_org_id = t.org_id
)
SELECT ... FROM org_tree ot
JOIN employee_ref er ON er.org_id = ot.org_id
JOIN employee_skill es ON es.employee_id = er.employee_id
```

### Co-occurrence / Self-Join (Endpoint 9)

Skill adjacency uses a self-join on `employee_skill` — for employees who know X, what else do they know?

```sql
SELECT s2.name, count(*) AS co_occurrence_count
FROM employee_skill es1
JOIN employee_skill es2 ON es1.employee_id = es2.employee_id
                       AND es1.skill_id != es2.skill_id
WHERE es1.skill_id = $1 AND es1.proficiency >= $2
GROUP BY s2.skill_id
ORDER BY co_occurrence_count DESC
```
