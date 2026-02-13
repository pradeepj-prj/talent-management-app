"""Shared test fixtures."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import create_pool, close_pool
from app.main import app


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def client():
    """Create a test client with a real DB pool (session-scoped)."""
    await create_pool()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await close_pool()
