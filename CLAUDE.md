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
- **Tests:** pytest + pytest-asyncio + httpx (48 integration tests against real DB)

### Architecture
```
app/routers/   → HTTP endpoint definitions (4 routers: employees, skills, talent_search, orgs)
app/services/  → Business logic and data transformation
app/queries/   → Raw SQL with asyncpg $1 positional parameters
app/models/    → Pydantic response schemas
app/static/    → Interactive API explorer (index.html)
app/config.py  → pydantic-settings (DB connection config)
app/database.py → asyncpg pool management (search_path: tm,public)
scripts/       → generate_tm_data.py (uses psycopg2, not asyncpg)
```

### Key Conventions
- All SQL is hand-written (no ORM) — enables recursive CTEs, window functions, relational division patterns.
- asyncpg uses `$1, $2` positional parameters (prepared statements), not `%s` or `:name`.
- The `tm` schema `search_path` is set at pool level — SQL queries don't need schema prefixes.
- Tests run against the real database (no mocks). Data must be generated first with `scripts/generate_tm_data.py --seed 42`.

### Deployment (Cloud Foundry — SAP BTP)
- **Live URL:** https://tm-skills-api.cfapps.ap10.hana.ondemand.com
- **CF org/space:** SEAIO_dial-3-0-zme762l7 / dev
- **Deployment files:** Procfile, manifest.yml, requirements.txt, runtime.txt, .cfignore
- **DB password:** Set via `cf set-env` (not in manifest.yml — never commit secrets)
- **Health check:** HTTP on `/health` endpoint
- To redeploy: `cf push` (password persists across pushes)
- To deploy fresh: `cf push --no-start && cf set-env tm-skills-api DB_PASSWORD "<pw>" && cf start tm-skills-api`

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
pytest tests/ -v                    # Run 48 integration tests
```
