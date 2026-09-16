import asyncio
import asyncpg

from app.config import settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    # If pool does not exist or was created on a now-closed event loop, re-create it
    if _pool is None or getattr(_pool, "_loop", None) is None or _pool._loop.is_closed():
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
        try:
            await _pool.close()
        except Exception:
            pass
        _pool = None
