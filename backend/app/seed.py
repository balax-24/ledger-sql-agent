"""
Seed script for Ledger demo database.
Populates customers, products, orders, and order_items with realistic sample data
AND an intentional, statistically detectable sales anomaly for live demos.

Connects using DATABASE_ADMIN_URL (or DATABASE_URL if privileged).
Can also export directly to `seed_data.sql` for PostgreSQL docker-entrypoint-initdb.d.
"""
import asyncio
import os
import random
from datetime import datetime, timedelta

import asyncpg
from dotenv import load_dotenv

load_dotenv()

random.seed(42)

REGIONS = ["North", "South", "East", "West", "Central"]

PRODUCTS_DATA = [
    # Electronics
    ("Apex Noise-Cancelling Headphones", "Electronics", 249.99, 110.00),
    ("Quantum Ultrawide Monitor 34-inch", "Electronics", 499.99, 260.00),
    ("ErgoMech Wireless Keyboard", "Electronics", 129.99, 55.00),
    ("Pulse Precision Optical Mouse", "Electronics", 69.99, 28.00),
    ("Titan USB-C Thunderbolt Dock", "Electronics", 179.99, 85.00),
    ("HyperSound 2.1 Speaker System", "Electronics", 149.99, 70.00),
    ("Nova Smart 4K Streaming Box", "Electronics", 89.99, 40.00),
    # Home & Kitchen
    ("BaristaTouch Espresso Machine", "Home & Kitchen", 299.99, 130.00),
    ("AeroPure HEPA Air Purifier", "Home & Kitchen", 189.99, 85.00),
    ("SmartBrew Thermal Coffee Maker", "Home & Kitchen", 99.99, 42.00),
    ("ChefPro Cast Iron Dutch Oven", "Home & Kitchen", 119.99, 50.00),
    ("Precision Sous Vide Cooker", "Home & Kitchen", 129.99, 60.00),
    ("HydroGlow Smart Water Kettle", "Home & Kitchen", 79.99, 32.00),
    ("Culinary Edge Damascus Knife Set", "Home & Kitchen", 219.99, 95.00),
    # Apparel
    ("All-Weather Tech Commuter Jacket", "Apparel", 169.99, 70.00),
    ("Merino Wool Thermal Sweater", "Apparel", 119.99, 48.00),
    ("UrbanStretch Tailored Chinos", "Apparel", 79.99, 30.00),
    ("Performance Flex Running Hoodie", "Apparel", 89.99, 35.00),
    ("StormShield Waterproof Trench", "Apparel", 199.99, 85.00),
    ("BreezeLite Organic Cotton Tee", "Apparel", 34.99, 12.00),
    ("TrailGrip All-Terrain Boots", "Apparel", 149.99, 65.00),
    # Sports
    ("Vortex Carbon Road Bike Helmet", "Sports", 139.99, 58.00),
    ("IronCore Pro Adjustable Dumbbells", "Sports", 299.99, 140.00),
    ("AeroFlex Yoga Mat Premium 6mm", "Sports", 59.99, 22.00),
    ("SummitTrek Ultralight Hiking Pack", "Sports", 129.99, 55.00),
    ("HydroMax Insulated Sport Bottle 1L", "Sports", 39.99, 15.00),
    ("Velocity Pro Resistance Bands Set", "Sports", 44.99, 18.00),
    ("GripMaster Climbing Chalk & Bag", "Sports", 29.99, 11.00),
    # Books
    ("Designing Data-Intensive Applications", "Books", 49.99, 25.00),
    ("The Pragmatic Programmer: 20th Anniv.", "Books", 45.00, 22.00),
    ("Staff Engineer: Leadership Beyond Track", "Books", 38.00, 18.00),
    ("Clean Code: Agile Software Craft", "Books", 42.50, 20.00),
    ("Database Internals: Distributed Systems", "Books", 55.00, 28.00),
    ("Systems Performance: Enterprise & Cloud", "Books", 65.00, 32.00),
    ("Building Microservices: 2nd Edition", "Books", 52.00, 26.00),
]

CUSTOMERS_DATA = [
    ("Apex Technologies Corp", "purchasing@apextech.com", "West"),
    ("Elena Rostova", "elena.rostova@gmail.com", "North"),
    ("Marcus Vance", "marcus.vance@vanceholdings.com", "Central"),
    ("Priya Sharma", "priya.sharma@techstar.in", "South"),
    ("David Chen", "david.chen@chenlogistics.com", "West"),
    ("Aaliyah Jenkins", "aaliyah.j@creativeedge.org", "East"),
    ("Jonathan Miller", "jonathan.miller@milleranalytics.com", "Central"),
    ("Sophia Martinez", "smartinez@globalcorp.net", "South"),
    ("Liam O'Connor", "liam.oconnor@emeraldmedia.ie", "North"),
    ("Chloe Dubois", "chloe.dubois@parisfinance.fr", "East"),
    ("Alexander Wright", "alex.wright@wrighteng.com", "West"),
    ("Fatima Al-Mansoor", "fatima.m@gulfconsulting.ae", "Central"),
    ("Lucas Silva", "lucas.silva@saopaulotech.br", "South"),
    ("Isabella Rossi", "i.rossi@milanodesign.it", "North"),
    ("Benjamin Taylor", "ben.taylor@taylorfirm.com", "East"),
    ("Ananya Patel", "ananya.patel@mumbaifinance.in", "South"),
    ("William Becker", "william.becker@beckerautomotive.de", "North"),
    ("Olivia Kim", "olivia.kim@seoulventures.kr", "West"),
    ("Noah Andersen", "noah.andersen@nordiccloud.dk", "Central"),
    ("Mia Johansson", "mia.j@stockholmlabs.se", "North"),
    ("James Wilson", "jwilson@wilsonlaw.com", "East"),
    ("Emily Watson", "emily.watson@watsonbiotech.com", "West"),
    ("Gabriel Santos", "gabriel.santos@riobusiness.br", "South"),
    ("Hannah Schmidt", "h.schmidt@berlinfin.de", "Central"),
    ("Ethan Moore", "ethan.moore@moorepartners.com", "East"),
    ("Zoe Takahashi", "zoe.t@tokyodev.jp", "West"),
    ("Daniel Evans", "daniel.evans@evanscapital.com", "North"),
    ("Grace Kelly", "grace.kelly@monacoluxury.mc", "South"),
    ("Matthew Harris", "mharris@harrismfg.com", "Central"),
    ("Ava Robinson", "ava.robinson@robinsonmedia.com", "East"),
    ("Ryan Clark", "ryan.clark@clarkconsulting.com", "West"),
    ("Lily Zhang", "lily.zhang@shanghaitech.cn", "East"),
    ("Samuel Lewis", "samuel.lewis@lewisfoundation.org", "North"),
    ("Samantha Walker", "swalker@walkerhealth.com", "Central"),
    ("Oliver Hall", "oliver.hall@halllogistics.co.uk", "South"),
    ("Victoria Allen", "victoria.allen@allenlaw.com", "West"),
    ("Henry Young", "henry.young@youngfintech.com", "East"),
    ("Maya Hernandez", "m.hernandez@mexicodev.mx", "South"),
    ("Sebastian King", "sking@kingenterprises.com", "North"),
    ("Natalia Kowalski", "natalia.k@warsawtech.pl", "Central"),
    ("Jack Wright", "jack.wright@wrightaudio.com", "West"),
    ("Ella Scott", "ella.scott@scottevents.com", "East"),
    ("Leo Green", "leo.green@greenenergy.co", "North"),
    ("Aria Adams", "aria.adams@adamsarchitects.com", "South"),
    ("Julian Baker", "julian.baker@bakermedia.com", "Central"),
    ("Nora Nelson", "nora.nelson@nelsondesign.com", "West"),
    ("Owen Carter", "owen.carter@carterrobotics.com", "East"),
    ("Stella Mitchell", "stella.m@mitchellventures.com", "North"),
    ("Luke Roberts", "luke.roberts@robertsfreight.com", "South"),
    ("Hazel Turner", "hazel.turner@turnerpublishing.com", "Central"),
]

STATUSES_WEIGHTED = (
    ["delivered"] * 55 + ["shipped"] * 20 + ["paid"] * 12 + ["pending"] * 8 + ["cancelled"] * 5
)


def generate_sql_seed_file(filepath: str):
    """Generate a standalone SQL seed script for Docker init or direct psql execution."""
    lines = [
        "-- Ledger Demo Seed Data with Deterministic Anomaly",
        "TRUNCATE order_items, orders, products, customers RESTART IDENTITY CASCADE;",
        "",
        "-- 1. Customers",
        "INSERT INTO customers (name, email, region, created_at) VALUES",
    ]

    base_date = datetime(2024, 6, 1, 10, 0, 0)
    customer_values = []
    for idx, (name, email, region) in enumerate(CUSTOMERS_DATA):
        c_date = base_date + timedelta(days=idx * 12, hours=random.randint(1, 10))
        esc_name = name.replace("'", "''")
        customer_values.append(f"  ('{esc_name}', '{email}', '{region}', '{c_date.strftime('%Y-%m-%d %H:%M:%S')}')")
    lines.append(",\n".join(customer_values) + ";\n")

    lines.append("-- 2. Products")
    lines.append("INSERT INTO products (name, category, price, cost) VALUES")
    prod_values = []
    for name, cat, price, cost in PRODUCTS_DATA:
        esc_name = name.replace("'", "''")
        prod_values.append(f"  ('{esc_name}', '{cat}', {price:.2f}, {cost:.2f})")
    lines.append(",\n".join(prod_values) + ";\n")

    # 3. Orders and Order Items across 12 months (September 2025 - August 2026)
    # Controlled Anomaly:
    # Month 2026-05 (May 2026) has 220 orders (~$38,000 revenue) -> clear spike!
    # Normal months have 60-70 orders (~$8,000 - $10,000 revenue).
    lines.append("-- 3. Orders & Order Items (with Controlled Anomaly in May 2026)")

    order_id = 1
    order_inserts = []
    item_inserts = []

    months = [
        (2025, 9, 65),
        (2025, 10, 68),
        (2025, 11, 72),
        (2025, 12, 85),  # slight holiday lift, but still baseline
        (2026, 1, 62),
        (2026, 2, 60),
        (2026, 3, 66),
        (2026, 4, 70),
        (2026, 5, 235), # *** MASSIVE CONTROLLED ANOMALY (3.5x regular volume) ***
        (2026, 6, 74),
        (2026, 7, 71),
        (2026, 8, 75),
    ]

    for year, month, order_count in months:
        days_in_month = 28 if month == 2 else (30 if month in (4, 6, 9, 11) else 31)
        for _ in range(order_count):
            day = random.randint(1, days_in_month)
            hour = random.randint(8, 21)
            minute = random.randint(0, 59)
            sec = random.randint(0, 59)
            order_date = f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{sec:02d}"

            # VIP customer gets more high-value orders
            if random.random() < 0.12:
                customer_id = 1  # Apex Technologies
            elif random.random() < 0.08:
                customer_id = 2  # Elena Rostova
            else:
                customer_id = random.randint(3, len(CUSTOMERS_DATA))

            status = random.choice(STATUSES_WEIGHTED)
            order_inserts.append(f"  ({customer_id}, '{order_date}', '{status}')")

            # 1-3 items per order
            n_items = random.choices([1, 2, 3], weights=[50, 35, 15])[0]
            chosen_prods = random.sample(range(1, len(PRODUCTS_DATA) + 1), k=n_items)
            for prod_id in chosen_prods:
                prod_price = PRODUCTS_DATA[prod_id - 1][2]
                qty = random.choices([1, 2, 3], weights=[70, 20, 10])[0]
                item_inserts.append(f"  ({order_id}, {prod_id}, {qty}, {prod_price:.2f})")

            order_id += 1

    lines.append("INSERT INTO orders (customer_id, order_date, status) VALUES")
    lines.append(",\n".join(order_inserts) + ";\n")

    # 3. Order Items in chunks of 500
    chunk_size = 500
    for i in range(0, len(item_inserts), chunk_size):
        chunk = item_inserts[i : i + chunk_size]
        lines.append("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES\n" + ",\n".join(chunk) + ";\n")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Generated SQL seed file: {filepath} ({order_id - 1} orders)")


async def seed():
    # Prefer admin connection string for seeding write operations
    db_url = os.environ.get("DATABASE_ADMIN_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set.")
        return

    print(f"Connecting to database to seed demo data...")
    try:
        conn = await asyncpg.connect(db_url)
    except Exception as e:
        print(f"Could not connect to database: {e}")
        return

    # Generate and execute SQL statements
    seed_sql_path = os.path.join(os.path.dirname(__file__), "..", "seed_data.sql")
    generate_sql_seed_file(seed_sql_path)

    with open(seed_sql_path, "r", encoding="utf-8") as f:
        sql_script = f.read()

    print("Executing seed statements...")
    await conn.execute(sql_script)
    await conn.close()
    print("Database seeding completed successfully!")


if __name__ == "__main__":
    # Generate seed SQL file first
    seed_file = os.path.join(os.path.dirname(__file__), "..", "seed_data.sql")
    generate_sql_seed_file(seed_file)
    asyncio.run(seed())
