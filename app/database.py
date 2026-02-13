"""asyncpg connection pool management."""

from collections.abc import AsyncIterator

import asyncpg
from asyncpg import Pool, Connection

from app.config import settings

pool: Pool | None = None


async def create_pool() -> Pool:
    """Create the asyncpg connection pool at startup."""
    global pool
    pool = await asyncpg.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        min_size=settings.db_min_pool,
        max_size=settings.db_max_pool,
        # Set search_path so all queries resolve tm.* tables without prefix
        server_settings={"search_path": "tm,public"},
    )
    return pool


async def close_pool() -> None:
    """Close the pool at shutdown."""
    global pool
    if pool:
        await pool.close()
        pool = None


async def get_connection() -> AsyncIterator[Connection]:
    """FastAPI dependency that yields a connection from the pool."""
    assert pool is not None, "Database pool not initialised"
    async with pool.acquire() as conn:
        yield conn
