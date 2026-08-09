import asyncpg

from app.config import settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=1,
            max_size=5,
            command_timeout=settings.query_timeout_seconds,
            statement_cache_size=0,
        )
    return _pool


async def close_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
