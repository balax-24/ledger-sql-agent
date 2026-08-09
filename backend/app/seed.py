"""
One-off seed script. Run with: python -m app.seed
Connects with the DATABASE_URL from .env (use the postgres owner role for
this script specifically, since it needs to INSERT — swap back to
agent_readonly for the app itself).
"""
import asyncio
import os
import random
from datetime import datetime, timedelta

import asyncpg
from dotenv import load_dotenv
from faker import Faker

load_dotenv()

fake = Faker()
Faker.seed(42)
random.seed(42)

REGIONS = ["North", "South", "East", "West", "Central"]
CATEGORIES = ["Electronics", "Home & Kitchen", "Apparel", "Sports", "Books"]
STATUSES_WEIGHTED = (
    ["delivered"] * 55 + ["shipped"] * 20 + ["paid"] * 12 + ["pending"] * 8 + ["cancelled"] * 5
)

N_CUSTOMERS = 60
N_PRODUCTS = 35
N_ORDERS = 900


async def seed():
    database_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(database_url)

    print("Clearing existing demo data...")
    await conn.execute("truncate order_items, orders, products, customers restart identity cascade")

    print(f"Inserting {N_CUSTOMERS} customers...")
    customer_ids = []
    for _ in range(N_CUSTOMERS):
        row = await conn.fetchrow(
            "insert into customers (name, email, region, created_at) values ($1, $2, $3, $4) returning id",
            fake.name(),
            fake.unique.email(),
            random.choice(REGIONS),
            fake.date_time_between(start_date="-2y", end_date="-3M"),
        )
        customer_ids.append(row["id"])

    print(f"Inserting {N_PRODUCTS} products...")
    product_rows = []  # (id, price)
    for _ in range(N_PRODUCTS):
        category = random.choice(CATEGORIES)
        cost = round(random.uniform(5, 150), 2)
        price = round(cost * random.uniform(1.3, 2.8), 2)
        row = await conn.fetchrow(
            "insert into products (name, category, price, cost) values ($1, $2, $3, $4) returning id, price",
            f"{fake.word().capitalize()} {category.split()[0]} {random.choice(['Pro', 'Lite', 'Max', 'Plus', ''])}".strip(),
            category,
            price,
            cost,
        )
        product_rows.append((row["id"], float(row["price"])))

    print(f"Inserting {N_ORDERS} orders with line items...")
    now = datetime.utcnow()
    for _ in range(N_ORDERS):
        # weight order dates towards the last 3 months so trend charts look alive
        days_back = int(random.triangular(0, 365, 20))
        order_date = now - timedelta(days=days_back, hours=random.randint(0, 23))
        customer_id = random.choice(customer_ids)
        status = random.choice(STATUSES_WEIGHTED)

        order_row = await conn.fetchrow(
            "insert into orders (customer_id, order_date, status) values ($1, $2, $3) returning id",
            customer_id,
            order_date,
            status,
        )
        order_id = order_row["id"]

        n_items = random.randint(1, 4)
        chosen = random.sample(product_rows, k=min(n_items, len(product_rows)))
        for product_id, price in chosen:
            await conn.execute(
                "insert into order_items (order_id, product_id, quantity, unit_price) values ($1, $2, $3, $4)",
                order_id,
                product_id,
                random.randint(1, 3),
                price,
            )

    await conn.close()
    print("Done. Seeded customers, products, orders, order_items.")


if __name__ == "__main__":
    asyncio.run(seed())
