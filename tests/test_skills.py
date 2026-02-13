"""Tests for skill-centric endpoints (3, 4, 6, 7, 9, 11)."""

import pytest

PYTHON_SKILL_ID = 1  # Python is skill_id=1 from the catalog


@pytest.mark.asyncio(loop_scope="session")
class TestSkillTaxonomy:
    """Endpoint 11: GET /tm/skills"""

    async def test_browse_all_skills(self, client):
        resp = await client.get("/tm/skills")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 93  # full catalog

    async def test_filter_by_category(self, client):
        resp = await client.get("/tm/skills?category=leadership")
        data = resp.json()
        assert data["total"] == 8
        assert all(s["category"] == "leadership" for s in data["skills"])

    async def test_search_by_name(self, client):
        resp = await client.get("/tm/skills?search=python")
        data = resp.json()
        assert data["total"] >= 1
        assert any("Python" in s["name"] for s in data["skills"])

    async def test_combined_filter(self, client):
        resp = await client.get("/tm/skills?category=tool&search=docker")
        data = resp.json()
        assert data["total"] >= 1
        assert all(s["category"] == "tool" for s in data["skills"])


@pytest.mark.asyncio(loop_scope="session")
class TestTopExperts:
    """Endpoint 3: GET /tm/skills/{id}/experts"""

    async def test_returns_experts(self, client):
        resp = await client.get(f"/tm/skills/{PYTHON_SKILL_ID}/experts?min_proficiency=4&limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["skill"]["name"] == "Python"
        assert len(data["experts"]) <= 5
        assert data["total_matching"] > 0

    async def test_experts_sorted_by_proficiency(self, client):
        data = (await client.get(f"/tm/skills/{PYTHON_SKILL_ID}/experts?min_proficiency=3")).json()
        experts = data["experts"]
        for i in range(len(experts) - 1):
            assert experts[i]["proficiency"] >= experts[i + 1]["proficiency"] or (
                experts[i]["proficiency"] == experts[i + 1]["proficiency"]
                and experts[i]["confidence"] >= experts[i + 1]["confidence"]
            )

    async def test_experts_meet_min_proficiency(self, client):
        data = (await client.get(f"/tm/skills/{PYTHON_SKILL_ID}/experts?min_proficiency=4")).json()
        for expert in data["experts"]:
            assert expert["proficiency"] >= 4

    async def test_404_for_unknown_skill(self, client):
        resp = await client.get("/tm/skills/99999/experts")
        assert resp.status_code == 404


@pytest.mark.asyncio(loop_scope="session")
class TestSkillCoverage:
    """Endpoint 4: GET /tm/skills/{id}/coverage"""

    async def test_returns_distribution(self, client):
        resp = await client.get(f"/tm/skills/{PYTHON_SKILL_ID}/coverage?min_proficiency=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["skill"]["name"] == "Python"
        assert len(data["distribution"]) == 6  # levels 0-5
        assert data["total_employees"] > 0

    async def test_distribution_levels_0_to_5(self, client):
        data = (await client.get(f"/tm/skills/{PYTHON_SKILL_ID}/coverage")).json()
        levels = [b["proficiency"] for b in data["distribution"]]
        assert levels == [0, 1, 2, 3, 4, 5]

    async def test_distribution_sums_to_total(self, client):
        data = (await client.get(f"/tm/skills/{PYTHON_SKILL_ID}/coverage")).json()
        bucket_sum = sum(b["count"] for b in data["distribution"])
        assert bucket_sum == data["total_employees"]

    async def test_employees_at_min_is_correct(self, client):
        data = (await client.get(f"/tm/skills/{PYTHON_SKILL_ID}/coverage?min_proficiency=3")).json()
        sum_above = sum(b["count"] for b in data["distribution"] if b["proficiency"] >= 3)
        assert data["employees_at_min"] == sum_above


@pytest.mark.asyncio(loop_scope="session")
class TestEvidenceBackedCandidates:
    """Endpoint 6: GET /tm/skills/{id}/candidates"""

    async def test_returns_candidates(self, client):
        resp = await client.get(
            f"/tm/skills/{PYTHON_SKILL_ID}/candidates?min_proficiency=3&min_evidence_strength=3"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["candidates"], list)

    async def test_candidates_have_strong_evidence(self, client):
        data = (await client.get(
            f"/tm/skills/{PYTHON_SKILL_ID}/candidates?min_proficiency=3&min_evidence_strength=4"
        )).json()
        for cand in data["candidates"]:
            assert cand["proficiency"] >= 3
            assert len(cand["top_evidence"]) > 0
            assert all(ev["signal_strength"] >= 4 for ev in cand["top_evidence"])


@pytest.mark.asyncio(loop_scope="session")
class TestStaleSkills:
    """Endpoint 7: GET /tm/skills/{id}/stale"""

    async def test_returns_stale_entries(self, client):
        resp = await client.get(f"/tm/skills/{PYTHON_SKILL_ID}/stale?older_than_days=365")
        assert resp.status_code == 200
        data = resp.json()
        assert data["older_than_days"] == 365
        assert data["total_stale"] == len(data["stale_entries"])

    async def test_stale_entries_are_actually_old(self, client):
        data = (await client.get(f"/tm/skills/{PYTHON_SKILL_ID}/stale?older_than_days=365")).json()
        for entry in data["stale_entries"]:
            assert entry["days_since_update"] >= 365


@pytest.mark.asyncio(loop_scope="session")
class TestSkillAdjacency:
    """Endpoint 9: GET /tm/skills/{id}/cooccurring"""

    async def test_returns_cooccurring(self, client):
        resp = await client.get(f"/tm/skills/{PYTHON_SKILL_ID}/cooccurring?min_proficiency=3&top=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["skill"]["name"] == "Python"
        assert len(data["cooccurring"]) <= 10

    async def test_cooccurring_sorted_by_count(self, client):
        data = (await client.get(f"/tm/skills/{PYTHON_SKILL_ID}/cooccurring?top=20")).json()
        counts = [s["co_occurrence_count"] for s in data["cooccurring"]]
        assert counts == sorted(counts, reverse=True)

    async def test_skill_not_in_own_cooccurrence(self, client):
        data = (await client.get(f"/tm/skills/{PYTHON_SKILL_ID}/cooccurring")).json()
        skill_ids = [s["skill_id"] for s in data["cooccurring"]]
        assert PYTHON_SKILL_ID not in skill_ids
