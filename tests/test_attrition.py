"""Tests for attrition prediction endpoints."""

import pytest

EMPLOYEE_ID = "EMP000001"  # Zen Hamilton — in 70% sample with seed=42
ENGINEERING_ORG = "ORG030"  # Engineering (parent of all eng sub-orgs)

RISK_LEVELS = {"low", "medium", "high", "critical"}
EXPECTED_FACTORS = {
    "Performance", "Tenure", "Employment Type", "Seniority",
    "Recent Promotion", "Skill Staleness", "Skill Breadth",
    "Leadership Development", "Evidence Currency",
}


@pytest.mark.asyncio(loop_scope="session")
class TestSingleEmployeeAttrition:
    """GET /tm/attrition/employees/{employee_id}"""

    async def test_returns_prediction(self, client):
        resp = await client.get(f"/tm/attrition/employees/{EMPLOYEE_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["employee"]["employee_id"] == EMPLOYEE_ID
        assert data["employee"]["display_name"] == "Zen Hamilton"
        assert 0 <= data["probability"] <= 0.95
        assert data["risk_level"] in RISK_LEVELS

    async def test_has_all_nine_factors(self, client):
        data = (await client.get(f"/tm/attrition/employees/{EMPLOYEE_ID}")).json()
        factor_names = {f["factor"] for f in data["factors"]}
        assert factor_names == EXPECTED_FACTORS

    async def test_factor_fields_complete(self, client):
        data = (await client.get(f"/tm/attrition/employees/{EMPLOYEE_ID}")).json()
        for f in data["factors"]:
            assert isinstance(f["factor"], str) and len(f["factor"]) > 0
            assert isinstance(f["value"], str)
            assert isinstance(f["multiplier"], (int, float))
            assert f["multiplier"] > 0
            assert isinstance(f["description"], str) and len(f["description"]) > 0

    async def test_404_for_unknown_employee(self, client):
        resp = await client.get("/tm/attrition/employees/EMP999999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    async def test_422_for_invalid_employee_id(self, client):
        resp = await client.get("/tm/attrition/employees/INVALID")
        assert resp.status_code == 422


@pytest.mark.asyncio(loop_scope="session")
class TestAllAttritionRisks:
    """GET /tm/attrition/employees"""

    async def test_returns_paginated_list(self, client):
        resp = await client.get("/tm/attrition/employees?limit=5&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["employees"]) <= 5
        assert data["limit"] == 5
        assert data["offset"] == 0
        assert data["total"] > 0

    async def test_sort_risk_desc(self, client):
        data = (await client.get("/tm/attrition/employees?limit=10&sort=risk_desc")).json()
        probs = [e["probability"] for e in data["employees"]]
        assert probs == sorted(probs, reverse=True)

    async def test_sort_risk_asc(self, client):
        data = (await client.get("/tm/attrition/employees?limit=10&sort=risk_asc")).json()
        probs = [e["probability"] for e in data["employees"]]
        assert probs == sorted(probs)

    async def test_sort_name(self, client):
        data = (await client.get("/tm/attrition/employees?limit=10&sort=name")).json()
        names = [e["employee"]["display_name"] for e in data["employees"]]
        assert names == sorted(names)

    async def test_min_risk_filter(self, client):
        data = (await client.get("/tm/attrition/employees?limit=200&min_risk=high")).json()
        for emp in data["employees"]:
            assert emp["risk_level"] in {"high", "critical"}

    async def test_pagination_offset(self, client):
        page1 = (await client.get("/tm/attrition/employees?limit=3&offset=0&sort=risk_desc")).json()
        page2 = (await client.get("/tm/attrition/employees?limit=3&offset=3&sort=risk_desc")).json()
        ids1 = {e["employee"]["employee_id"] for e in page1["employees"]}
        ids2 = {e["employee"]["employee_id"] for e in page2["employees"]}
        assert ids1.isdisjoint(ids2), "Pages should not overlap"
        assert page1["total"] == page2["total"], "Total should be consistent"


@pytest.mark.asyncio(loop_scope="session")
class TestHighRiskEmployees:
    """GET /tm/attrition/high-risk"""

    async def test_returns_above_threshold(self, client):
        resp = await client.get("/tm/attrition/high-risk?threshold=0.3&limit=50")
        assert resp.status_code == 200
        data = resp.json()
        for emp in data["employees"]:
            assert emp["probability"] >= 0.3

    async def test_sorted_by_risk_desc(self, client):
        data = (await client.get("/tm/attrition/high-risk?threshold=0.2&limit=20")).json()
        probs = [e["probability"] for e in data["employees"]]
        assert probs == sorted(probs, reverse=True)

    async def test_default_threshold_is_025(self, client):
        data = (await client.get("/tm/attrition/high-risk?limit=50")).json()
        for emp in data["employees"]:
            assert emp["probability"] >= 0.25


@pytest.mark.asyncio(loop_scope="session")
class TestOrgAttritionSummary:
    """GET /tm/attrition/orgs/{org_unit_id}/summary"""

    async def test_returns_summary(self, client):
        resp = await client.get(f"/tm/attrition/orgs/{ENGINEERING_ORG}/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["org_id"] == ENGINEERING_ORG
        assert data["org_name"] == "Engineering"
        assert data["total_employees"] > 0
        assert 0 <= data["avg_probability"] <= 0.95

    async def test_risk_distribution_sums_to_total(self, client):
        data = (await client.get(f"/tm/attrition/orgs/{ENGINEERING_ORG}/summary")).json()
        dist = data["risk_distribution"]
        total = dist["low"] + dist["medium"] + dist["high"] + dist["critical"]
        assert total == data["total_employees"]

    async def test_top_risk_sorted_desc(self, client):
        data = (await client.get(f"/tm/attrition/orgs/{ENGINEERING_ORG}/summary?top_risk_limit=5")).json()
        assert len(data["top_risk"]) <= 5
        probs = [e["probability"] for e in data["top_risk"]]
        assert probs == sorted(probs, reverse=True)

    async def test_404_for_unknown_org(self, client):
        resp = await client.get("/tm/attrition/orgs/ORG999/summary")
        assert resp.status_code == 404


@pytest.mark.asyncio(loop_scope="session")
class TestEmployeeNameSearch:
    """GET /tm/employees/search"""

    async def test_search_returns_matching_results(self, client):
        resp = await client.get("/tm/employees/search?name=Hamilton")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        names = [e["display_name"] for e in data["employees"]]
        assert any("Hamilton" in n for n in names)

    async def test_partial_match(self, client):
        resp = await client.get("/tm/employees/search?name=ham")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_no_results_for_nonsense(self, client):
        resp = await client.get("/tm/employees/search?name=zzxxyy999")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["employees"] == []

    async def test_422_for_short_query(self, client):
        resp = await client.get("/tm/employees/search?name=a")
        assert resp.status_code == 422
