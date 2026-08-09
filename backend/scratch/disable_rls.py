import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def main():
    # Use the owner connection string
    db_url = "postgresql://postgres.cqdvtypfmoeqlnrfafaa:Mb5xcxCL8hoAygMr@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
    conn = await asyncpg.connect(db_url)
    
    print("Disabling RLS on tables...")
    for table in ['customers', 'products', 'orders', 'order_items']:
        await conn.execute(f"alter table {table} disable row level security")
        print(f"Disabled RLS on {table}")
        
    await conn.close()
    print("Done!")

if __name__ == '__main__':
    asyncio.run(main())
