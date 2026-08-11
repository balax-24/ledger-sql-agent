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


async def _attempt_self_correction(failed_sql: str, error_message: str) -> str | None:
    """Attempts to correct a failing SQL SELECT query using the schema and error message."""
    try:
        from app.gemini_client import generate_text
        from app.tools.schema_tool import get_schema_data
        
        # Get schema definition to help the LLM correct table/column references
        schema = await get_schema_data()
        
        prompt = (
            "You are an expert PostgreSQL Database Administrator and Query Optimizer.\n"
            "The following read-only SQL query failed to execute against the database.\n\n"
            f"--- FAILED SQL QUERY ---\n{failed_sql}\n\n"
            f"--- DATABASE ERROR ---\n{error_message}\n\n"
            f"--- DATABASE SCHEMA ---\n{schema}\n\n"
            "Correct the SQL query so it runs successfully and resolves the error.\n"
            "Ensure the query remains a read-only SELECT query.\n"
            "Output ONLY the corrected SQL query. Do not wrap it in quotes, markdown code blocks, or include any extra text."
        )
        
        corrected_sql = await generate_text(prompt)
        if corrected_sql:
            corrected_sql = corrected_sql.strip()
            # If wrapped in code block like ```sql ... ```, extract it
            if "```" in corrected_sql:
                start_idx = corrected_sql.find("```")
                if start_idx != -1:
                    next_newline = corrected_sql.find("\n", start_idx)
                    if next_newline != -1:
                        end_idx = corrected_sql.find("```", next_newline)
                        if end_idx != -1:
                            corrected_sql = corrected_sql[next_newline:end_idx].strip()
            return corrected_sql
    except Exception:
        # Fall back gracefully if anything fails during correction
        pass
    return None


async def execute_query(sql: str, reasoning: str = "") -> dict:
    """Tool entrypoint. `reasoning` is accepted but only used for the
    transparency log the frontend shows — it's not part of query safety."""
    async def run_sql(query_str: str):
        pool = await get_pool()
        async with pool.acquire() as conn:
            return await asyncio.wait_for(
                conn.fetch(query_str), timeout=settings.query_timeout_seconds
            )

    self_corrected = False
    original_sql = sql
    original_error = None

    try:
        stmt = _validate_select_only(sql)
    except UnsafeQueryError as exc:
        original_error = str(exc)
        if "Could not parse SQL" in original_error:
            # Attempt local self-correction!
            corrected_sql = await _attempt_self_correction(sql, original_error)
            if corrected_sql:
                try:
                    stmt = _validate_select_only(corrected_sql)
                    sql = corrected_sql
                    self_corrected = True
                except Exception:
                    return {"success": False, "error_type": "unsafe_query", "message": original_error}
            else:
                return {"success": False, "error_type": "unsafe_query", "message": original_error}
        else:
            return {"success": False, "error_type": "unsafe_query", "message": original_error}

    safe_sql = _apply_row_limit(stmt, settings.query_row_limit)

    try:
        rows = await run_sql(safe_sql)
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error_type": "timeout",
            "message": f"Query exceeded {settings.query_timeout_seconds}s. Try a narrower filter or aggregate first.",
        }
    except (asyncpg.exceptions.UndefinedColumnError,
            asyncpg.exceptions.UndefinedTableError,
            asyncpg.exceptions.PostgresSyntaxError) as exc:
        original_error = str(exc)
        # Attempt local self-correction!
        corrected_sql = await _attempt_self_correction(safe_sql, original_error)
        if corrected_sql:
            try:
                # Validate that the corrected query is still a read-only SELECT
                corrected_stmt = _validate_select_only(corrected_sql)
                corrected_safe_sql = _apply_row_limit(corrected_stmt, settings.query_row_limit)
                rows = await run_sql(corrected_safe_sql)
                safe_sql = corrected_safe_sql
                self_corrected = True
            except Exception as retry_exc:
                err_type = "syntax_error"
                if isinstance(exc, asyncpg.exceptions.UndefinedColumnError):
                    err_type = "unknown_column"
                elif isinstance(exc, asyncpg.exceptions.UndefinedTableError):
                    err_type = "unknown_table"
                return {"success": False, "error_type": err_type, "message": original_error}
        else:
            err_type = "syntax_error"
            if isinstance(exc, asyncpg.exceptions.UndefinedColumnError):
                err_type = "unknown_column"
            elif isinstance(exc, asyncpg.exceptions.UndefinedTableError):
                err_type = "unknown_table"
            return {"success": False, "error_type": err_type, "message": original_error}
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
        "self_corrected": self_corrected,
        "original_sql": original_sql,
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

