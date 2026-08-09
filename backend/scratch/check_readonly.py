import asyncio
from app.db import get_pool, close_pool
from dotenv import load_dotenv

load_dotenv()

async def main():
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check current user and database
        user = await conn.fetchval("select current_user")
        db = await conn.fetchval("select current_database()")
        schema = await conn.fetchval("select current_schema()")
        print(f"Connected as User: {user}, Database: {db}, Schema: {schema}")
        
        # Check tables
        tables = await conn.fetch("select table_schema, table_name from information_schema.tables where table_schema = 'public'")
        print("Visible tables in public schema:")
        for t in tables:
            print(f" - {t['table_schema']}.{t['table_name']}")
            
        # Try select count on customers
        try:
            count = await conn.fetchval("select count(*) from customers")
            print(f"select count(*) from customers: {count}")
        except Exception as e:
            print("Failed select from customers:", e)
            
    await close_pool()

if __name__ == '__main__':
    asyncio.run(main())
