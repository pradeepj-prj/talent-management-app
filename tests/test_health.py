"""Tests for health endpoint."""

import pytest


@pytest.mark.asyncio(loop_scope="session")
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["db"] == "connected"
