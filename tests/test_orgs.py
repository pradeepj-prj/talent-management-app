"""Tests for org-centric endpoints (Endpoint 12)."""

import pytest

ENGINEERING_ORG = "ORG030"  # Engineering (parent of all eng sub-orgs)
SOFTWARE_ORG = "ORG031B"    # Product Dev - Software (leaf node)
PYTHON_SKILL_ID = 1


@pytest.mark.asyncio(loop_scope="session")
class TestOrgSkillSummary:
    """Endpoint 12a: GET /tm/orgs/{id}/skills/summary"""

    async def test_returns_summary(self, client):
        resp = await client.get(f"/tm/orgs/{ENGINEERING_ORG}/skills/summary?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["org"]["org_id"] == ENGINEERING_ORG
        assert data["org"]["org_name"] == "Engineering"
        assert data["includes_children"] is True
        assert data["total_profiled_employees"] > 0
        assert len(data["top_skills"]) <= 10

    async def test_parent_org_includes_children(self, client):
        parent = (await client.get(f"/tm/orgs/{ENGINEERING_ORG}/skills/summary")).json()
        child = (await client.get(f"/tm/orgs/{SOFTWARE_ORG}/skills/summary")).json()
        # Parent org should have more employees than a child
        assert parent["total_profiled_employees"] >= child["total_profiled_employees"]

    async def test_skill_summary_fields(self, client):
        data = (await client.get(f"/tm/orgs/{ENGINEERING_ORG}/skills/summary")).json()
        for skill in data["top_skills"]:
            assert "skill_id" in skill
            assert "name" in skill
            assert "category" in skill
            assert skill["employee_count"] > 0
            assert 0 <= skill["avg_proficiency"] <= 5

    async def test_404_for_unknown_org(self, client):
        resp = await client.get("/tm/orgs/ORG999/skills/summary")
        assert resp.status_code == 404


@pytest.mark.asyncio(loop_scope="session")
class TestOrgSkillExperts:
    """Endpoint 12b: GET /tm/orgs/{id}/skills/{skill_id}/experts"""

    async def test_returns_experts(self, client):
        resp = await client.get(
            f"/tm/orgs/{SOFTWARE_ORG}/skills/{PYTHON_SKILL_ID}/experts?min_proficiency=3"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["org"]["org_id"] == SOFTWARE_ORG
        assert data["skill_name"] == "Python"
        assert data["total_matching"] >= len(data["experts"])

    async def test_experts_meet_min_proficiency(self, client):
        data = (await client.get(
            f"/tm/orgs/{SOFTWARE_ORG}/skills/{PYTHON_SKILL_ID}/experts?min_proficiency=4"
        )).json()
        for expert in data["experts"]:
            assert expert["proficiency"] >= 4

    async def test_experts_are_in_correct_org(self, client):
        data = (await client.get(
            f"/tm/orgs/{SOFTWARE_ORG}/skills/{PYTHON_SKILL_ID}/experts?min_proficiency=1"
        )).json()
        for expert in data["experts"]:
            assert expert["org_name"] == "Product Dev - Software"

    async def test_404_for_unknown_org(self, client):
        resp = await client.get(f"/tm/orgs/ORG999/skills/{PYTHON_SKILL_ID}/experts")
        assert resp.status_code == 404

    async def test_404_for_unknown_skill(self, client):
        resp = await client.get(f"/tm/orgs/{SOFTWARE_ORG}/skills/99999/experts")
        assert resp.status_code == 404
