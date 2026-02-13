"""Tests for multi-skill talent search (Endpoint 5)."""

import pytest


@pytest.mark.asyncio(loop_scope="session")
class TestTalentSearch:
    """Endpoint 5: GET /tm/talent/search"""

    async def test_two_skill_search(self, client):
        resp = await client.get("/tm/talent/search?skills=Python,SQL&min_proficiency=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"]["skill_names"] == ["Python", "SQL"]
        assert data["query"]["min_proficiency"] == 3
        assert data["query"]["results_count"] == len(data["results"])

    async def test_all_results_have_all_skills(self, client):
        data = (await client.get("/tm/talent/search?skills=Python,SQL&min_proficiency=3")).json()
        for hit in data["results"]:
            skill_names = {s["skill_name"] for s in hit["matched_skills"]}
            assert "Python" in skill_names
            assert "SQL" in skill_names
            for s in hit["matched_skills"]:
                assert s["proficiency"] >= 3

    async def test_three_skill_search_narrows_results(self, client):
        two = (await client.get("/tm/talent/search?skills=Python,SQL&min_proficiency=3")).json()
        three = (await client.get("/tm/talent/search?skills=Python,SQL,Docker&min_proficiency=3")).json()
        # Adding more skills can only reduce or maintain the result count
        assert three["query"]["results_count"] <= two["query"]["results_count"]

    async def test_high_proficiency_narrows_results(self, client):
        low = (await client.get("/tm/talent/search?skills=Python,SQL&min_proficiency=3")).json()
        high = (await client.get("/tm/talent/search?skills=Python,SQL&min_proficiency=5")).json()
        assert high["query"]["results_count"] <= low["query"]["results_count"]

    async def test_case_insensitive_skill_names(self, client):
        resp = await client.get("/tm/talent/search?skills=python,sql&min_proficiency=3")
        assert resp.status_code == 200
        assert resp.json()["query"]["results_count"] > 0

    async def test_404_for_unknown_skill(self, client):
        resp = await client.get("/tm/talent/search?skills=Cobol&min_proficiency=1")
        assert resp.status_code == 404
        assert "skills" in resp.json()["detail"].lower()

    async def test_400_for_empty_skills(self, client):
        resp = await client.get("/tm/talent/search?skills=&min_proficiency=1")
        assert resp.status_code == 400
