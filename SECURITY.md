# Security Assessment — TM Skills API

> **Date:** 2026-02-15 (updated after deployment)
> **Status:** All 6 remediation phases implemented and deployed
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

### Implemented Controls

| Control | Status | Details |
|---------|--------|---------|
| Authentication | ✅ Implemented | API key via `X-API-Key` header — 401 if missing, 403 if invalid. Disabled when `API_KEYS` env var is empty. `/health` exempt for CF probes. |
| CORS Policy | ✅ Hardened | Origins restricted to production domain, `allow_credentials=False`, methods limited to `GET, OPTIONS` |
| Security Headers | ✅ Implemented | `X-Frame-Options: DENY`, `HSTS`, `CSP`, `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `Referrer-Policy` |
| Rate Limiting | ✅ Implemented | 60 requests/minute per client IP via `slowapi`, `X-Forwarded-For` aware for CF Go Router |
| Audit Logging | ✅ Implemented | Structured access logs: method, path, status, duration, client IP, masked API key |
| Input Format Validation | ✅ Implemented | Regex on employee IDs (`^EMP\d{6}$`), org IDs (`^ORG\d{1,4}[A-Z]?$`), skill category enum, search length caps |

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
                              API Key auth barrier
                              Rate limiting (60/min)
                              Security headers
                              Access logging
```

### Threat Scenarios

| # | Threat | Likelihood | Impact | Mitigation |
|---|--------|-----------|--------|------------|
| T1 | **Unauthenticated data exfiltration** | High | High | ✅ API key required on all data endpoints (Phase 2) |
| T2 | **CORS credential theft** | Medium | High | ✅ Origins restricted, credentials disabled (Phase 1) |
| T3 | **DB pool exhaustion (DoS)** | Medium | Medium | ✅ 60/min rate limit per client IP (Phase 4) |
| T4 | **Clickjacking** | Low | Low | ✅ `X-Frame-Options: DENY` + `frame-ancestors 'none'` (Phase 3) |
| T5 | **Response caching of PII** | Low | Medium | ✅ `Cache-Control: no-store` (Phase 3) |
| T6 | **Employee ID enumeration** | Medium | Medium | ✅ API key required + input validation rejects invalid formats (Phases 2, 6) |
| T7 | **Information leakage via headers** | Low | Low | ✅ Security headers added, stack traces suppressed (Phase 3) |

---

## 4. Remediation Status

All six phases implemented and deployed:

| Phase | What | Status | Addresses |
|-------|------|--------|-----------|
| **Phase 1** | CORS Hardening | ✅ Done | T2 — config-driven origins, credentials disabled, methods restricted |
| **Phase 2** | API Key Authentication | ✅ Done | T1, T6 — `X-API-Key` header, disabled by default, `/health` exempt |
| **Phase 3** | Security Response Headers | ✅ Done | T4, T5, T7 — 6 headers via `SecurityHeadersMiddleware` |
| **Phase 4** | Rate Limiting | ✅ Done | T3 — `slowapi` at 60/min, `X-Forwarded-For` aware |
| **Phase 5** | Request Logging / Audit Trail | ✅ Done | All — structured `key=value` access logs |
| **Phase 6** | Input Validation Hardening | ✅ Done | T6 — regex on IDs, category enum, length caps |

### Deployment Notes

- Secrets managed via `deploy.sh` — generates API key, prompts for DB password
- `manifest.yml` must NOT contain secrets (overwrites `cf set-env` on every `cf push`)
- `./deploy.sh --rotate` to generate a new API key

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
