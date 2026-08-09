import asyncio
from app.db import get_pool, close_pool
from dotenv import load_dotenv

load_dotenv()

async def main():
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check if RLS is enabled
        rls = await conn.fetch("""
            select tablename, rowsecurity 
            from pg_tables 
            where schemaname = 'public'
        """)
        print("Row level security on tables:")
        for r in rls:
            print(f" - {r['tablename']}: RLS enabled = {r['rowsecurity']}")
            
        # Check permissions/grants
        grants = await conn.fetch("""
            select grantee, table_name, privilege_type 
            from information_schema.role_table_grants 
            where table_schema = 'public' and grantee = 'agent_readonly'
        """)
        print("Grants for agent_readonly:")
        for g in grants:
            print(f" - {g['table_name']}: {g['privilege_type']}")
            
    await close_pool()

if __name__ == '__main__':
    asyncio.run(main())
