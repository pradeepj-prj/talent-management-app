"""Tests for employee-centric endpoints (1, 2, 8, 10)."""

import pytest

# EMP000001 (Zen Hamilton) is in the 70% sample with seed=42
EMPLOYEE_ID = "EMP000001"


@pytest.mark.asyncio(loop_scope="session")
class TestEmployeeSkillProfile:
    """Endpoint 1: GET /tm/employees/{id}/skills"""

    async def test_returns_skill_profile(self, client):
        resp = await client.get(f"/tm/employees/{EMPLOYEE_ID}/skills")
        assert resp.status_code == 200
        data = resp.json()
        assert data["employee"]["employee_id"] == EMPLOYEE_ID
        assert data["employee"]["display_name"] == "Zen Hamilton"
        assert data["total_skills"] == len(data["skills"])
        assert data["total_skills"] > 0

    async def test_skills_have_required_fields(self, client):
        resp = await client.get(f"/tm/employees/{EMPLOYEE_ID}/skills")
        data = resp.json()
        for skill in data["skills"]:
            assert "skill_id" in skill
            assert "skill_name" in skill
            assert "proficiency" in skill
            assert 0 <= skill["proficiency"] <= 5
            assert 0 <= skill["confidence"] <= 100
            assert skill["source"] in ("self", "manager", "assessment", "certification", "peer", "inferred", "system")

    async def test_skills_sorted_by_proficiency_desc(self, client):
        resp = await client.get(f"/tm/employees/{EMPLOYEE_ID}/skills")
        skills = resp.json()["skills"]
        for i in range(len(skills) - 1):
            # Primary sort: proficiency DESC
            assert skills[i]["proficiency"] >= skills[i + 1]["proficiency"] or (
                skills[i]["proficiency"] == skills[i + 1]["proficiency"]
            )

    async def test_404_for_unknown_employee(self, client):
        resp = await client.get("/tm/employees/NOEXIST/skills")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio(loop_scope="session")
class TestSkillEvidence:
    """Endpoint 2: GET /tm/employees/{id}/skills/{skill_id}/evidence"""

    async def test_returns_evidence(self, client):
        # First get a skill_id that the employee has
        profile = (await client.get(f"/tm/employees/{EMPLOYEE_ID}/skills")).json()
        skill_id = profile["skills"][0]["skill_id"]

        resp = await client.get(f"/tm/employees/{EMPLOYEE_ID}/skills/{skill_id}/evidence")
        assert resp.status_code == 200
        data = resp.json()
        assert data["employee"]["employee_id"] == EMPLOYEE_ID
        assert data["skill_id"] == skill_id
        assert isinstance(data["evidence"], list)

    async def test_evidence_fields(self, client):
        profile = (await client.get(f"/tm/employees/{EMPLOYEE_ID}/skills")).json()
        skill_id = profile["skills"][0]["skill_id"]

        data = (await client.get(f"/tm/employees/{EMPLOYEE_ID}/skills/{skill_id}/evidence")).json()
        for ev in data["evidence"]:
            assert "evidence_id" in ev
            assert ev["evidence_type"] in (
                "certification", "project", "assessment",
                "manager_validation", "peer_endorsement", "portfolio", "work_history", "other",
            )
            assert 1 <= ev["signal_strength"] <= 5

    async def test_404_for_unassigned_skill(self, client):
        resp = await client.get(f"/tm/employees/{EMPLOYEE_ID}/skills/99999/evidence")
        assert resp.status_code == 404


@pytest.mark.asyncio(loop_scope="session")
class TestTopSkills:
    """Endpoint 8: GET /tm/employees/{id}/top-skills"""

    async def test_returns_top_skills(self, client):
        resp = await client.get(f"/tm/employees/{EMPLOYEE_ID}/top-skills?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["skills"]) <= 5
        assert data["limit"] == 5

    async def test_default_limit_is_10(self, client):
        resp = await client.get(f"/tm/employees/{EMPLOYEE_ID}/top-skills")
        data = resp.json()
        assert data["limit"] == 10


@pytest.mark.asyncio(loop_scope="session")
class TestEvidenceInventory:
    """Endpoint 10: GET /tm/employees/{id}/evidence"""

    async def test_returns_all_evidence(self, client):
        resp = await client.get(f"/tm/employees/{EMPLOYEE_ID}/evidence")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_items"] == len(data["evidence"])
        assert data["total_items"] > 0

    async def test_evidence_includes_skill_info(self, client):
        data = (await client.get(f"/tm/employees/{EMPLOYEE_ID}/evidence")).json()
        for ev in data["evidence"]:
            assert "skill_id" in ev
            assert "skill_name" in ev

    async def test_404_for_unknown_employee(self, client):
        resp = await client.get("/tm/employees/NOEXIST/evidence")
        assert resp.status_code == 404
