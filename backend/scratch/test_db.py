import asyncio
import os
from dotenv import load_dotenv
from app.db import get_pool, close_pool

load_dotenv()

async def main():
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Query table sizes
            for table in ['customers', 'products', 'orders', 'order_items']:
                count = await conn.fetchval(f"select count(*) from {table}")
                print(f"Table {table}: {count} rows")
    except Exception as e:
        print("DB connection failed:", e)
    finally:
        await close_pool()

if __name__ == '__main__':
    asyncio.run(main())
