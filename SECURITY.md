# Security Assessment — TM Skills API

> **Date:** 2026-02-15
> **Application:** Talent Management Skills API (FastAPI)
> **Deployment:** Cloud Foundry on SAP BTP (ap10 region)
> **Scope:** Read-only API — 12 GET endpoints serving employee talent/skill data

---

## 1. Current Security Posture

### What's Protected

| Control | Status | Details |
|---------|--------|---------|
| SQL Injection | ✅ Protected | All queries use asyncpg prepared statements (`$1`, `$2`) — parameterised at the protocol level |
| Output Sanitization | ✅ Protected | Pydantic response models enforce typed output — no raw DB rows leak to clients |
| Stack Trace Suppression | ✅ Protected | Global `exception_handler(Exception)` returns generic `{"detail": "Internal server error"}` |
| TLS in Transit | ✅ Protected | Cloud Foundry Go Router terminates TLS — all external traffic is HTTPS |

### What's Missing

| Control | Status | Risk | Details |
|---------|--------|------|---------|
| Authentication | ❌ None | **Critical** | Any client can read all endpoints — no API keys, tokens, or credentials required |
| CORS Policy | ❌ Misconfigured | **High** | `allow_origins=["*"]` with `allow_credentials=True` — browsers will send cookies to any origin |
| Security Headers | ❌ None | **Medium** | No `X-Frame-Options`, `HSTS`, `CSP`, `Cache-Control`, or `X-Content-Type-Options` |
| Rate Limiting | ❌ None | **Medium** | DB pool max is 10 — a single client can exhaust all connections |
| Audit Logging | ❌ None | **Medium** | No visibility into who accesses what data |
| Input Format Validation | ❌ Minimal | **Low** | Employee/org IDs accept arbitrary strings — unnecessary DB queries for invalid formats |

---

## 2. Data Sensitivity Assessment

The API exposes **employee talent management data** — this is sensitive HR/PII information.

### Data Exposed by Endpoint

| Endpoint | Data | Sensitivity |
|----------|------|-------------|
| `GET /tm/employees/{id}/skills` | Employee name, job title, org, all skill proficiency scores | **High** — PII + performance data |
| `GET /tm/employees/{id}/skills/{id}/evidence` | Certifications, project history, peer endorsements | **High** — career evidence |
| `GET /tm/employees/{id}/top-skills` | Employee's strongest skills ranked | **High** — competitive intelligence |
| `GET /tm/employees/{id}/evidence` | Full evidence inventory across all skills | **High** — comprehensive career record |
| `GET /tm/skills` | Skill catalog (names, categories) | **Low** — organisational metadata |
| `GET /tm/skills/{id}/experts` | Employee names + proficiency for a skill | **High** — who's good at what |
| `GET /tm/skills/{id}/coverage` | Aggregate counts (no individual PII) | **Low** — statistical |
| `GET /tm/skills/{id}/candidates` | Employees with evidence for a skill | **High** — PII + evidence |
| `GET /tm/skills/{id}/stale` | Employees with outdated skill records | **Medium** — staleness indicators |
| `GET /tm/skills/{id}/cooccurring` | Aggregate skill correlations | **Low** — statistical |
| `GET /tm/talent/search` | Multi-skill employee search with PII | **High** — targeted talent lookup |
| `GET /tm/orgs/{id}/skills/summary` | Org-level aggregates | **Low** — statistical |
| `GET /tm/orgs/{id}/skills/{id}/experts` | Named employees within an org | **High** — PII within org context |

**Summary:** 8 of 12 endpoints expose individual employee PII. This data should not be publicly accessible.

---

## 3. Threat Model

### Attack Surface

```
Internet → CF Go Router (TLS) → FastAPI App → asyncpg → PostgreSQL
                                     ↑
                              No auth barrier here
```

### Threat Scenarios

| # | Threat | Likelihood | Impact | Current Mitigation |
|---|--------|-----------|--------|-------------------|
| T1 | **Unauthenticated data exfiltration** — Attacker scrapes all employee skill data via sequential ID enumeration | High | High | None — all endpoints are public |
| T2 | **CORS credential theft** — Malicious site makes cross-origin requests with user cookies | Medium | High | None — CORS allows all origins with credentials |
| T3 | **DB pool exhaustion (DoS)** — Automated requests exhaust the 10-connection pool | Medium | Medium | None — no rate limiting |
| T4 | **Clickjacking** — API explorer embedded in malicious iframe | Low | Low | None — no `X-Frame-Options` header |
| T5 | **Response caching** — Proxies/browsers cache sensitive employee data | Low | Medium | None — no `Cache-Control: no-store` |
| T6 | **Employee ID enumeration** — Sequential `EMP000001`, `EMP000002`... pattern is guessable | Medium | Medium | None — IDs are predictable and no auth required |
| T7 | **Information leakage via headers** — Server version, framework details | Low | Low | FastAPI doesn't leak much by default |

---

## 4. Remediation Plan

Six implementation phases, each a single reviewable commit:

| Phase | What | Addresses |
|-------|------|-----------|
| **Phase 1** | CORS Hardening | T2 — restrict origins, disable credentials, limit methods |
| **Phase 2** | API Key Authentication | T1, T6 — require `X-API-Key` header for all endpoints |
| **Phase 3** | Security Response Headers | T4, T5, T7 — add `X-Frame-Options`, `HSTS`, `CSP`, `Cache-Control` |
| **Phase 4** | Rate Limiting | T3 — per-client request throttling via `slowapi` |
| **Phase 5** | Request Logging / Audit Trail | All — structured access logs with masked API keys |
| **Phase 6** | Input Validation Hardening | T6 — regex patterns on `employee_id`, `org_unit_id` |

---

## 5. Future Considerations

These items are **out of scope** for the current hardening effort but should be considered for production:

### OAuth2 / JWT Authentication (Phase 7)
- Bind an SAP BTP XSUAA service instance
- Use `sap-xssec` Python package to verify JWTs from the `Authorization: Bearer <token>` header
- Map XSUAA role collections to endpoint access (e.g., `tm-viewer`, `tm-admin`)
- The API Key approach (Phase 2) is designed so OAuth2 can be added alongside it — auth lives in a single dependency (`app/auth.py`)

### Database User Separation
- Create a read-only PostgreSQL user (`tm_reader`) with `SELECT`-only grants on the `tm` schema
- The current `hr_app` user has broader permissions than needed for a read-only API

### Dependency Scanning
- Add `pip-audit` or `safety` to CI/CD pipeline
- Scan for known vulnerabilities in `asyncpg`, `fastapi`, `uvicorn`, `pydantic-settings`

### Secret Management
- Move DB credentials from environment variables to a proper secrets manager
- SAP BTP offers Credential Store service for this purpose

### Network Segmentation
- Consider restricting DB access to only the CF application's egress IP range
- PostgreSQL `pg_hba.conf` or security group rules
