# Talent Management App — Project Learnings

This document captures key architectural decisions, technical learnings, and patterns discovered during the development and deployment of the TM Skills API.

---

## 1. Architecture Decisions

### Schema Separation (tm vs public)

The TM skill data lives in a dedicated `tm` schema within the same `hr_data` PostgreSQL database that holds the HR master data (in the `public` schema). This mirrors how real enterprises keep HR systems separate from talent management systems.

**Why this matters:**
- The `tm.employee_ref` table is a local sync of HR employee data, so the API is self-contained at runtime (no cross-schema joins at query time).
- The `tm.org_unit_ref` table is similarly synced, enabling recursive org hierarchy traversal without touching the HR schema.
- The `search_path` is set to `tm,public` at the connection pool level (`server_settings`), so SQL queries don't need schema prefixes.

### Raw SQL over ORM

All database queries are hand-written SQL in dedicated `queries/` modules rather than using an ORM (SQLAlchemy, Tortoise, etc.).

**Why:**
- Full control over PostgreSQL-specific features: recursive CTEs (endpoint 12), window functions, `HAVING` clauses for relational division (endpoint 5), self-joins for co-occurrence (endpoint 9).
- asyncpg uses positional parameters (`$1`, `$2`) which are prepared statements — safe from SQL injection and cached by PostgreSQL for performance.
- The query complexity (recursive CTEs, self-joins, relational division) would be awkward or impossible to express idiomatically in most ORMs.

### Layered Architecture

The app follows a clean three-layer pattern:
```
routers/ → services/ → queries/
```
- **Routers:** FastAPI endpoint definitions, parameter validation, HTTP concerns.
- **Services:** Business logic, data transformation, orchestration of multiple queries.
- **Queries:** Pure SQL strings + asyncpg execution. Each module maps to one business domain.

This separation makes it easy to test, modify queries without touching HTTP logic, and swap out the database layer if needed.

### asyncpg (not psycopg2) for the API

The API uses `asyncpg` — a native async PostgreSQL driver — rather than `psycopg2` (which is used only by the data generation script).

**Why:**
- FastAPI is an async framework. Using an async driver means DB queries don't block the event loop, enabling true concurrent request handling.
- asyncpg is significantly faster than psycopg2 for read-heavy workloads due to its native protocol implementation (binary protocol, no libpq dependency).

### pydantic-settings for Configuration

`pydantic-settings` provides type-safe configuration with automatic environment variable binding:
- Reads from `.env` file locally (developer convenience).
- Reads from OS environment variables in production (Cloud Foundry, Docker, etc.).
- The `.env` file is optional — if absent, it silently falls back to env vars. This is what made the Cloud Foundry deployment require **zero code changes**.

---

## 2. SQL Patterns Worth Remembering

### Relational Division (Endpoint 5 — Multi-Skill AND Search)

Finding employees who have **all** of a set of skills is a classic "relational division" problem:
```sql
SELECT es.employee_id
FROM employee_skill es
WHERE es.skill_id = ANY($1) AND es.proficiency >= $2
GROUP BY es.employee_id
HAVING count(DISTINCT es.skill_id) = $3  -- must match ALL skills
```
The `HAVING count(DISTINCT ...) = N` ensures AND semantics (all skills required), not OR.

### Recursive CTE (Endpoint 12 — Org Hierarchy Traversal)

Walking the org tree to include all child departments:
```sql
WITH RECURSIVE org_tree AS (
    SELECT org_id FROM org_unit_ref WHERE org_id = $1
    UNION ALL
    SELECT o.org_id FROM org_unit_ref o
    JOIN org_tree t ON o.parent_org_id = t.org_id
)
SELECT ... FROM org_tree ot
JOIN employee_ref er ON er.org_id = ot.org_id
```
This pattern is reusable for any hierarchical data (reporting chains, category trees, BOM structures).

### Self-Join for Co-occurrence (Endpoint 9)

Finding skills that commonly appear together:
```sql
SELECT s2.name, count(*) AS co_occurrence_count
FROM employee_skill es1
JOIN employee_skill es2 ON es1.employee_id = es2.employee_id
                       AND es1.skill_id != es2.skill_id
WHERE es1.skill_id = $1 AND es1.proficiency >= $2
GROUP BY s2.skill_id
ORDER BY co_occurrence_count DESC
```
This is a market-basket analysis pattern — useful for recommendations ("people who know X also know Y").

---

## 3. Data Generation Learnings

### Realistic Data via Correlation

The `generate_tm_data.py` script creates believable data by correlating skills with employee attributes:
- **Job-group matching:** Software engineers get Python/Docker, sales reps get Salesforce/Pipeline Management.
- **Seniority correlation:** Senior employees get more skills (4–20 range), higher proficiency, and leadership skills (seniority 3+).
- **Staleness injection:** ~17% of skills have `last_updated_at` older than 1 year, enabling the governance/freshness endpoint (7) to return meaningful results.

### Seeded Randomness

Using `random.seed(42)` ensures reproducible data generation. All 48 integration tests rely on deterministic data — changing the seed would break test assertions that check specific employee IDs and counts.

### Generated Data Statistics (seed=42, 70% sample)

| Metric | Value |
|--------|-------|
| Employees profiled | 1,348 / 1,927 active |
| Skills in catalog | 93 (5 categories) |
| Skill assignments | 13,410 (avg 9.9/employee) |
| Evidence items | 18,794 (avg 1.4/skill) |
| Stale skills (>1yr) | 2,253 (16.8%) |

---

## 4. Testing Approach

### Integration Tests Against Real Data

All 48 tests run against the actual PostgreSQL database with generated data — no mocks. This catches real SQL issues (syntax errors, type mismatches, missing indexes) that unit tests with mocks would miss.

**Trade-off:** Tests require DB access and generated data to be present. The `conftest.py` creates a session-scoped asyncpg pool shared across all tests.

### Test Organization

Tests mirror the router structure:
- `test_health.py` — Health endpoint and DB connectivity
- `test_employees.py` — Employee-centric endpoints (1, 2, 8, 10)
- `test_skills.py` — Skill-centric endpoints (3, 4, 6, 7, 9, 11)
- `test_search.py` — Multi-skill search (5)
- `test_orgs.py` — Org-level queries (12)

---

## 5. Cloud Foundry Deployment Learnings

### Zero Code Changes for CF Deployment

The app required **no modifications** for Cloud Foundry deployment. This worked because:
1. `pydantic-settings` reads env vars by default (`.env` file is optional).
2. `StaticFiles(directory="app/static")` uses a relative path that resolves correctly — CF's Python buildpack sets CWD to the app root.
3. The `/health` endpoint already existed for CF's HTTP health check.

### CF Deployment Files

Five files were added to the project root:

| File | Purpose |
|------|---------|
| `Procfile` | Start command: `uvicorn` bound to `0.0.0.0:$PORT` |
| `manifest.yml` | App config: memory, buildpack, health check, env vars |
| `requirements.txt` | Production deps (CF Python buildpack reads this) |
| `runtime.txt` | Python version pin (`python-3.10.x`) |
| `.cfignore` | Excludes dev artifacts from upload |

### First-Push Chicken-and-Egg Problem

`cf set-env` requires the app to already exist, but the first `cf push` creates the app and starts it immediately. On first deploy with a blank `DB_PASSWORD` in manifest, the app crashes with `InvalidPasswordError`.

**Solution:** After the first push, set the password and restart:
```bash
cf set-env tm-skills-api DB_PASSWORD "<password>"
cf restart tm-skills-api
```

**Better alternative for future first deploys:**
```bash
cf push --no-start
cf set-env tm-skills-api DB_PASSWORD "<password>"
cf start tm-skills-api
```

### CF Environment Variable Precedence

Env vars set via `cf set-env` **override** those in `manifest.yml`. So on subsequent `cf push` runs, the password persists — no need to re-set it. The blank `DB_PASSWORD` in the manifest serves as documentation, not a functional default.

### SAP BTP Network Considerations

The external PostgreSQL (AWS ap-southeast-1) is reachable from SAP BTP Cloud Foundry because:
- CF apps can make outbound connections to internet-accessible IPs.
- The AWS security group must allow inbound on port 5432 from the CF NAT egress IPs.
- If the DB were behind a private network, SAP Cloud Connector would be needed.

### Resource Sizing

- **256M memory** is sufficient for the async FastAPI + asyncpg stack.
- **1 worker** is appropriate — the async event loop handles concurrency without multiple processes.
- **DB pool max of 5** (reduced from 10 locally) suits CF's constrained container resources.

---

## 6. API Design Patterns

### Consistent Response Shapes

All endpoints return structured JSON with predictable patterns:
- List endpoints return arrays with enriched objects (employee details joined in).
- Detail endpoints return nested objects (skill + evidence grouped).
- Search endpoint returns matches with per-skill detail for each employee.

### The Interactive Explorer

A custom `app/static/index.html` serves as an interactive API explorer (accessible at root URL `/`). This replaces the default Swagger UI with a more user-friendly interface tailored to the TM business questions.

### Health Check Design

The `/health` endpoint does more than return 200 — it actively checks DB connectivity:
```json
{"status": "healthy", "db": "connected"}
{"status": "unhealthy", "db": "pool not initialised"}
{"status": "unhealthy", "db": "<error message>"}
```
This makes it immediately clear whether the API is truly functional or just running.

---

## 7. Dependency Management

### Two Package Managers

- `pyproject.toml` — The canonical dependency spec (PEP 621). Used for local development with `pip install -e ".[dev,generator]"`.
- `requirements.txt` — Production-only deps for Cloud Foundry. The CF Python buildpack reads this reliably (it doesn't understand `pyproject.toml` extras).

Both must be kept in sync. The `requirements.txt` intentionally omits dev/generator extras.

### Dependency Groups

| Group | Packages | Purpose |
|-------|----------|---------|
| core | fastapi, uvicorn, asyncpg, pydantic-settings | Production runtime |
| dev | pytest, pytest-asyncio, httpx, ruff | Testing and linting |
| generator | psycopg2-binary | Data generation script (sync driver) |

---

## 8. Live Deployment

The app is deployed and accessible at:
- **URL:** https://tm-skills-api.cfapps.ap10.hana.ondemand.com
- **Health:** https://tm-skills-api.cfapps.ap10.hana.ondemand.com/health
- **Explorer:** https://tm-skills-api.cfapps.ap10.hana.ondemand.com/static/index.html
- **CF Region:** SAP BTP ap10 (Singapore)
- **Org:** SEAIO_dial-3-0-zme762l7 / space: dev
