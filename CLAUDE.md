This project is about creating a talent management database and then creating an app that runs some predefined queries on the database and returns the results through an API.

In this directory you can find tm_schema.sql for the database schema.

In this directory you can find tm_business_questions.md for an idea of what business questions can be asked, these have to be converted to SQL and exposed through an API endpoint.

For the API, FastAPI can be used. For the database, you can use postgres.

Git repo (remote): git@github.com:pradeepj-prj/talent-management-app.git

For this project, during plan mode you can plan the whole thing, but I want changes to be made incrementally for my review. After something is changed, please go through a review cycle. Stop and ask if review is needed.

The data for this project will be linked to another project called HR-Data-Generator, please look at the README.md, CLAUDE.md, DATAMODEL.md to understand more about the employee database. The goal would be to create a TM database for a subset of the employees in that database.

## Project Status

The TM Skills API is **fully implemented and deployed**. See LEARNINGS.md for detailed technical notes.

### Tech Stack
- **API:** FastAPI + uvicorn (async)
- **Database driver:** asyncpg (async, binary protocol, positional params `$1, $2`)
- **Configuration:** pydantic-settings (reads .env locally, env vars in production)
- **Database:** PostgreSQL `hr_data` database, `tm` schema (separate from HR `public` schema)
- **Security:** API key auth, CORS whitelist, rate limiting (slowapi), security headers, access logging
- **Tests:** pytest + pytest-asyncio + httpx (70 integration tests against real DB)

### Architecture
```
app/routers/       → HTTP endpoint definitions (5 routers: employees, skills, talent_search, orgs, attrition)
app/services/      → Business logic and data transformation
app/queries/       → Raw SQL with asyncpg $1 positional parameters
app/models/        → Pydantic response schemas
app/auth.py        → API key authentication dependency (X-API-Key header)
app/middleware/     → AccessLogMiddleware (structured request logging)
app/static/        → Interactive API explorer (index.html) with API key input
app/config.py      → pydantic-settings (DB, CORS, auth, rate limiting config)
app/database.py    → asyncpg pool management (search_path: tm,public)
scripts/           → generate_tm_data.py (uses psycopg2, not asyncpg)
deploy.sh          → CF deployment script with auto-generated API key
```

### Key Conventions
- All SQL is hand-written (no ORM) — enables recursive CTEs, LATERAL joins, window functions, relational division patterns.
- asyncpg uses `$1, $2` positional parameters (prepared statements), not `%s` or `:name`.
- The `tm` schema `search_path` is set at pool level — SQL queries don't need schema prefixes.
- Tests run against the real database (no mocks). Data must be generated first with `scripts/generate_tm_data.py --seed 42`.
- Secrets (`DB_PASSWORD`, `API_KEYS`) must **never** go in `manifest.yml` — they are set via `cf set-env` or `deploy.sh`.
- `pydantic-settings` cannot parse `set[str]` from plain env var strings — use `str` field + `@property` to parse comma-separated values.

### Deployment (Cloud Foundry — SAP BTP)
- **Live URL:** https://tm-skills-api.cfapps.ap10.hana.ondemand.com
- **CF org/space:** SEAIO_dial-3-0-zme762l7 / dev
- **Deployment files:** Procfile, manifest.yml, requirements.txt, runtime.txt, .cfignore, deploy.sh
- **Secrets:** `DB_PASSWORD` and `API_KEYS` set via `cf set-env` (never in manifest.yml)
- **Health check:** HTTP on `/health` endpoint (exempt from API key auth)
- **Deploy:** `./deploy.sh` (generates API key on first run, prompts for DB password, handles `cf push` + `cf set-env`)
- **Rotate API key:** `./deploy.sh --rotate`
- **Local secret files:** `.api-key` and `.db-password` (both gitignored and cfignored)
- **IMPORTANT:** `manifest.yml` must NOT contain `DB_PASSWORD` — `cf push` applies the manifest and overwrites any value previously set via `cf set-env`

### Database Connection
- **Host:** 13.228.165.215 (AWS ap-southeast-1)
- **Database:** hr_data
- **User:** hr_app
- **Local config:** .env file (not committed)
- **CF config:** Environment variables in manifest.yml + cf set-env for secrets

### Running Locally
```bash
pip install -e ".[dev,generator]"   # Install all deps
cp .env.example .env                # Configure DB credentials
uvicorn app.main:app --reload       # Start dev server at localhost:8000
pytest tests/ -v                    # Run 70 integration tests
```

### Employee Name Search

- `GET /tm/employees/search?name=&limit=` — case-insensitive partial match on `display_name` in `tm.employee_ref`
- `name` param requires `min_length=2`; `limit` defaults to 20 (max 100)
- Returns `EmployeeSearchResult` with `employees: list[EmployeeRef]` and `total: int`
- Route is defined **before** `/{employee_id}` routes in `app/routers/employees.py` to avoid path conflicts

### Attrition Prediction

A deterministic rules-based model predicting employee attrition risk. Not ML — uses a formula with 9 weighted factors combining HR master data and TM-specific features.

**Formula:** `P(leave) = 0.12 × perf × tenure × emp_type × seniority × promotion × skill_staleness × skill_breadth × leadership × evidence_currency` (capped at 0.95)

**Factors (from HR `public.*` and TM `tm.*` tables):**

| # | Factor | Source Table | Multiplier Range |
|---|--------|-------------|-----------------|
| 1 | Performance | `public.employee_performance` (latest rating) | 0.4 – 2.5 |
| 2 | Tenure | `public.employee` (hire_date) | 0.5 – 1.8 |
| 3 | Employment type | `public.employee` (employment_type) | 1.0 – 2.0 |
| 4 | Seniority | `tm.employee_ref` (seniority_level) | 0.5 – 1.3 |
| 5 | Recent promotion | `public.employee_job_assignment` (start_date in last 18mo) | 0.4 – 1.0 |
| 6 | Skill staleness | `tm.employee_skill` (avg days since update) | 0.8 – 1.6 |
| 7 | Skill breadth | `tm.employee_skill` (count) | 0.8 – 1.5 |
| 8 | Leadership dev | `tm.employee_skill` + `tm.skill` (leadership category, proficiency≥3) | 0.6 – 1.2 |
| 9 | Evidence currency | `tm.skill_evidence` (dated within 12mo) | 0.7 – 1.2 |

**Risk classification:** <0.10 → low, 0.10-0.25 → medium, 0.25-0.50 → high, 0.50-0.95 → critical

**Endpoints:**
- `GET /tm/attrition/employees/{employee_id}` — single employee prediction with full factor breakdown
- `GET /tm/attrition/employees?limit=&offset=&min_risk=&sort=` — paginated list (sort: risk_desc/risk_asc/name)
- `GET /tm/attrition/high-risk?threshold=&limit=&offset=` — employees above probability threshold (default 0.25)
- `GET /tm/attrition/orgs/{org_unit_id}/summary?top_risk_limit=` — org-level risk distribution + top N riskiest

**Key implementation notes:**
- Feature extraction uses LATERAL joins for batch queries (`GET_EMPLOYEE_FEATURES_BATCH`) and CTEs for single-employee queries
- `public.*` tables must be explicitly prefixed in SQL since `search_path` is `tm,public`
- All predictions include explainable factor breakdowns (factor name, raw value, multiplier, human-readable description)
- The API explorer sidebar "Attrition Prediction" group has 4 panels:
  - **Risk Dashboard** — summary cards, filters, sortable paginated table with expandable factor breakdowns
  - **Employee Lookup** — name search (calls `/tm/employees/search`) + ID lookup (calls `/tm/attrition/employees/{id}`) with full prediction + factor breakdown
  - **High-Risk Employees** — threshold/limit filter, calls `/tm/attrition/high-risk`, table with expandable factors
  - **Org Summary** — org ID input, calls `/tm/attrition/orgs/{id}/summary`, risk distribution cards + top-risk table
