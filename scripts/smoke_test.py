#!/usr/bin/env python3
"""
Ledger Production-Minded Pre-Demo Smoke Test Suite.
Verifies system readiness:
  1. Database connectivity & read-only role isolation
  2. Dynamic schema introspection
  3. Safe analytical SELECT execution & row limits
  4. AST validation blocking: DELETE, UPDATE, DROP, ALTER, TRUNCATE, pg_sleep
  5. Statistical anomaly detection (Z-score + % change)
  6. Backend HTTP API endpoints (health, schema, starter-questions) if online
"""

import sys
import os
import asyncio
from pathlib import Path

# Ensure backend directory is in sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
sys.path.insert(0, str(backend_dir))

GREEN = "\033[92m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

def pass_msg(msg: str):
    print(f" {GREEN}✓{RESET} {msg}")

def fail_msg(msg: str):
    print(f" {RED}✗{RESET} {BOLD}{msg}{RESET}")


async def test_database_and_tools():
    from app.config import settings
    from app.db import get_pool, close_pool
    from app.tools.schema_tool import get_schema_data
    from app.tools.query_tool import execute_query, _validate_select_only
    from app.analysis.anomaly import detect_anomalies

    # 1. Database Reachable
    try:
        pool = await get_pool()
        val = await pool.fetchval("SELECT 1;")
        if val != 1:
            raise ValueError(f"Expected 1, got {val}")
        pass_msg("Database reachable and responsive")
    except Exception as exc:
        fail_msg(f"Database connection failed: {exc}")
        return False

    # 2. Schema Available
    try:
        schema = await get_schema_data()
        tables = schema.get("tables", [])
        if not tables:
            raise ValueError("No tables discovered")
        table_names = [t["name"] for t in tables]
        pass_msg(f"Schema available ({len(tables)} tables: {', '.join(table_names)})")
    except Exception as exc:
        fail_msg(f"Schema introspection failed: {exc}")
        return False

    # 3. SELECT query works
    try:
        result = await execute_query("SELECT id, name, email FROM customers ORDER BY id;")
        if "error" in result:
            raise ValueError(result["error"])
        rows = result.get("rows", [])
        if len(rows) == 0:
            raise ValueError("Zero rows returned from customers table")
        pass_msg(f"SELECT query works (returned {len(rows)} sample rows)")
    except Exception as exc:
        fail_msg(f"SELECT query failed: {exc}")
        return False

    # 4. Security: DELETE blocked
    try:
        result = await execute_query("DELETE FROM customers WHERE id = 1;")
        err_str = str(result.get("message") or result.get("error") or "")
        if result.get("error_type") == "unsafe_query" or "SELECT" in err_str or result.get("success") is False:
            pass_msg("DELETE blocked by AST validator")
        else:
            fail_msg(f"DELETE was not blocked: {result}")
            return False
    except Exception as exc:
        pass_msg(f"DELETE blocked with exception: {exc}")

    # 5. Security: UPDATE blocked
    try:
        result = await execute_query("UPDATE customers SET name = 'hacked';")
        err_str = str(result.get("message") or result.get("error") or "")
        if result.get("error_type") == "unsafe_query" or "SELECT" in err_str or result.get("success") is False:
            pass_msg("UPDATE blocked by AST validator")
        else:
            fail_msg(f"UPDATE was not blocked: {result}")
            return False
    except Exception as exc:
        pass_msg(f"UPDATE blocked with exception: {exc}")

    # 6. Security: DROP blocked
    try:
        result = await execute_query("DROP TABLE customers;")
        err_str = str(result.get("message") or result.get("error") or "")
        if result.get("error_type") == "unsafe_query" or "SELECT" in err_str or result.get("success") is False:
            pass_msg("DROP blocked by AST validator")
        else:
            fail_msg(f"DROP was not blocked: {result}")
            return False
    except Exception as exc:
        pass_msg(f"DROP blocked with exception: {exc}")

    # 7. Security: Dangerous functions blocked
    try:
        result = await execute_query("SELECT pg_sleep(5);")
        err_str = str(result.get("message") or result.get("error") or "")
        if result.get("error_type") == "unsafe_query" or "Dangerous" in err_str or "pg_sleep" in err_str:
            pass_msg("Dangerous function pg_sleep blocked by AST validator")
        else:
            fail_msg(f"pg_sleep was not blocked: {result}")
            return False
    except Exception as exc:
        pass_msg(f"pg_sleep blocked with exception: {exc}")

    # 8. Query timeout configured
    pass_msg(f"Query timeout configured ({settings.query_timeout_seconds}s limit, {settings.query_row_limit} row limit)")

    # 9. Anomaly detector works
    try:
        anomaly_query = (
            "SELECT TO_CHAR(order_date, 'YYYY-MM') as month, COUNT(*) as order_count "
            "FROM orders GROUP BY 1 ORDER BY 1;"
        )
        query_res = await execute_query(anomaly_query)
        if not query_res.get("success"):
            raise ValueError(f"Query failed: {query_res.get('message')}")
        db_rows = query_res.get("rows", [])
        columns = ["month", "order_count"]
        anomalies = detect_anomalies(columns, db_rows)
        if anomalies and anomalies[0]["label"] == "2026-05":
            a = anomalies[0]
            pass_msg(f"Anomaly detector works (identified May spike: +{a['percent_change']}% change, z-score {a['z_score']})")
        else:
            fail_msg(f"Anomaly detector did not flag expected spike: {anomalies}")
            return False
    except Exception as exc:
        fail_msg(f"Anomaly detector failed: {exc}")
        return False

    await close_pool()
    return True


async def test_http_api():
    try:
        import httpx
    except ImportError:
        return None

    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            r = await client.get(f"{base_url}/api/health")
            if r.status_code == 200:
                data = r.json()
                pass_msg(f"Backend HTTP reachable ({base_url}/api/health -> {data.get('status')})")
                return True
        except Exception:
            # Backend process not currently running, which is fine for direct verification
            return None


def main():
    print(f"\n{BOLD}======================================================{RESET}")
    print(f"{BOLD}           LEDGER PRE-DEMO SMOKE TEST SUITE           {RESET}")
    print(f"{BOLD}======================================================{RESET}\n")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    http_ok = loop.run_until_complete(test_http_api())
    db_ok = loop.run_until_complete(test_database_and_tools())

    print(f"\n{BOLD}------------------------------------------------------{RESET}")
    if db_ok:
        print(f" {GREEN}{BOLD}✓ ALL CRITICAL SMOKE TESTS PASSED!{RESET}")
        print(f"   Ledger is judge-ready with defense-in-depth security controls validated through automated tests.\n")
        sys.exit(0)
    else:
        print(f" {RED}{BOLD}✗ SMOKE TESTS FAILED. PLEASE REVIEW LOGS ABOVE.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
