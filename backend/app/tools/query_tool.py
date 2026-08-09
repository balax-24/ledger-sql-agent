import asyncio
import decimal
import datetime

import asyncpg
import sqlglot
from sqlglot import expressions as exp

from app.config import settings
from app.db import get_pool


class UnsafeQueryError(ValueError):
    pass


def _validate_select_only(sql: str) -> exp.Select:
    """Parse with sqlglot and reject anything that isn't a single read-only
    SELECT. This is a real parser, not a regex/keyword blocklist — it
    won't be fooled by comments, string literals containing 'DROP', etc.
    The read-only DB role is the second, independent layer of defense.
    """
    try:
        statements = sqlglot.parse(sql, read="postgres")
    except Exception as exc:  # noqa: BLE001
        raise UnsafeQueryError(f"Could not parse SQL: {exc}") from exc

    if len(statements) != 1:
        raise UnsafeQueryError("Only a single SQL statement is allowed per call.")

    stmt = statements[0]
    if stmt is None or not isinstance(stmt, exp.Select):
        raise UnsafeQueryError("Only SELECT statements are allowed.")

    # Belt-and-suspenders: reject any write-shaped subexpression that could
    # theoretically hide inside a CTE (e.g. a data-modifying CTE in some dialects).
    forbidden = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter)
    for node in stmt.walk():
        if isinstance(node, forbidden):
            raise UnsafeQueryError("Query contains a disallowed write operation.")

    return stmt


def _apply_row_limit(stmt: exp.Select, limit: int) -> str:
    existing_limit = stmt.args.get("limit")
    if existing_limit is None:
        stmt = stmt.limit(limit)
    else:
        try:
            current = int(existing_limit.expression.this)
            if current > limit:
                stmt = stmt.limit(limit)
        except (AttributeError, ValueError):
            stmt = stmt.limit(limit)
    return stmt.sql(dialect="postgres")


def _jsonable(value):
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return value


async def execute_query(sql: str, reasoning: str = "") -> dict:
    """Tool entrypoint. `reasoning` is accepted but only used for the
    transparency log the frontend shows — it's not part of query safety."""
    try:
        stmt = _validate_select_only(sql)
    except UnsafeQueryError as exc:
        return {"success": False, "error_type": "unsafe_query", "message": str(exc)}

    safe_sql = _apply_row_limit(stmt, settings.query_row_limit)

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await asyncio.wait_for(
                conn.fetch(safe_sql), timeout=settings.query_timeout_seconds
            )
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error_type": "timeout",
            "message": f"Query exceeded {settings.query_timeout_seconds}s. Try a narrower filter or aggregate first.",
        }
    except asyncpg.exceptions.UndefinedColumnError as exc:
        return {"success": False, "error_type": "unknown_column", "message": str(exc)}
    except asyncpg.exceptions.UndefinedTableError as exc:
        return {"success": False, "error_type": "unknown_table", "message": str(exc)}
    except asyncpg.exceptions.PostgresSyntaxError as exc:
        return {"success": False, "error_type": "syntax_error", "message": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error_type": "query_failed", "message": str(exc)}

    columns = list(rows[0].keys()) if rows else []
    result_rows = [{k: _jsonable(v) for k, v in dict(r).items()} for r in rows]

    return {
        "success": True,
        "sql_executed": safe_sql,
        "columns": columns,
        "rows": result_rows,
        "row_count": len(result_rows),
        "truncated": len(result_rows) >= settings.query_row_limit,
    }


# Keep alias for compatibility
run_sql_query = execute_query


EXECUTE_QUERY_TOOL_DECLARATION = {
    "name": "execute_query",
    "description": (
        "Execute a read-only SQL SELECT against the database and return the "
        "results. Only SELECT is permitted — no INSERT/UPDATE/DELETE/DDL. "
        "Call get_schema first if you don't already know table or column names."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "sql": {"type": "string", "description": "A single valid PostgreSQL SELECT statement."},
            "reasoning": {
                "type": "string",
                "description": "One sentence on what this query is trying to find — shown to the user for transparency.",
            },
        },
        "required": ["sql", "reasoning"],
    },
}

