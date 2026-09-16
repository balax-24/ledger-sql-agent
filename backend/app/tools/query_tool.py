import asyncio
import datetime
import decimal
import time

import asyncpg
import sqlglot
from sqlglot import expressions as exp

from app.config import settings
from app.db import get_pool
from app.logger import logger


class UnsafeQueryError(ValueError):
    """Raised when a query fails AST security validation."""
    pass


FORBIDDEN_EXPRESSIONS = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.TruncateTable,
    exp.Command,
    exp.Transaction,
    exp.Commit,
    exp.Rollback,
)

DANGEROUS_FUNCTIONS = {
    "pg_sleep",
    "pg_terminate_backend",
    "pg_cancel_backend",
    "pg_read_file",
    "pg_write_file",
    "pg_read_binary_file",
    "pg_ls_dir",
    "dblink",
    "dblink_exec",
    "dblink_connect",
    "lo_export",
    "lo_import",
    "query_to_xml",
    "query_to_xmlschema",
    "pg_reload_conf",
    "pg_rotate_logfile",
    "system",
}


def _validate_select_only(sql: str) -> exp.Select:
    """Parse with sqlglot and enforce read-only SELECT policy.

    Security Checks:
    1. Parsing: Valid PostgreSQL syntax with exactly 1 statement.
    2. Root statement: Must be an exp.Select (allows CTEs, UNION, subqueries).
    3. Forbidden write/DDL nodes: Walk AST and reject Insert, Update, Delete, Drop, Alter, Truncate.
    4. Row-locking: Reject SELECT ... FOR UPDATE / FOR SHARE clauses.
    5. Side-effect functions: Reject pg_sleep, pg_read_file, dblink, etc.
    """
    if not sql or not sql.strip():
        raise UnsafeQueryError("Query cannot be empty.")

    try:
        statements = sqlglot.parse(sql, read="postgres")
    except Exception as exc:  # noqa: BLE001
        raise UnsafeQueryError(f"Could not parse SQL: {exc}") from exc

    if not statements or statements[0] is None:
        raise UnsafeQueryError("Query contains no valid SQL statements.")

    if len(statements) != 1:
        raise UnsafeQueryError("Only a single SQL statement is allowed per call.")

    stmt = statements[0]
    if not isinstance(stmt, (exp.Select, exp.Union)):
        raise UnsafeQueryError("Only SELECT statements are allowed.")

    # 1. Walk AST for write / DDL operations
    for node in stmt.walk():
        if isinstance(node, FORBIDDEN_EXPRESSIONS):
            raise UnsafeQueryError(
                f"Query contains disallowed write/DDL operation: {node.key.upper()}."
            )

        # 2. Check for locking clauses (e.g. SELECT ... FOR UPDATE / FOR SHARE)
        if isinstance(node, exp.Lock):
            raise UnsafeQueryError("Row locking clauses (FOR UPDATE/SHARE) are strictly forbidden.")

        # 3. Check for dangerous side-effect functions
        if isinstance(node, (exp.Anonymous, exp.Func, exp.UserDefinedFunction)):
            func_name = (node.name or "").lower()
            if func_name in DANGEROUS_FUNCTIONS:
                raise UnsafeQueryError(f"Function '{func_name}' is forbidden for security.")

    # Check root level locks as well
    if stmt.args.get("locks"):
        raise UnsafeQueryError("Row locking clauses (FOR UPDATE/SHARE) are strictly forbidden.")

    return stmt


def _apply_row_limit(stmt: exp.Select, limit: int) -> str:
    """Ensure the query has an explicit LIMIT clause not exceeding `limit`."""
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
    """Attempts to correct a failing SQL query using schema context and the error message.
    The resulting query MUST still undergo full AST security validation.
    """
    logger.info("Attempting SQL self-correction for error: %s", error_message)
    try:
        from app.gemini_client import generate_text
        from app.tools.schema_tool import get_schema_data

        schema = await get_schema_data()

        prompt = (
            "You are an expert PostgreSQL Database Administrator.\n"
            "The following read-only SQL query failed to execute against the database.\n\n"
            f"--- FAILED SQL QUERY ---\n{failed_sql}\n\n"
            f"--- DATABASE ERROR ---\n{error_message}\n\n"
            f"--- DATABASE SCHEMA ---\n{schema}\n\n"
            "Correct the SQL query so it runs successfully and resolves the error.\n"
            "CRITICAL: The query MUST remain a read-only SELECT query.\n"
            "Output ONLY the corrected SQL query. Do not wrap it in markdown code blocks or quotes."
        )

        corrected_sql = await generate_text(prompt)
        if corrected_sql:
            corrected_sql = corrected_sql.strip()
            if "```" in corrected_sql:
                start_idx = corrected_sql.find("```")
                if start_idx != -1:
                    next_newline = corrected_sql.find("\n", start_idx)
                    if next_newline != -1:
                        end_idx = corrected_sql.find("```", next_newline)
                        if end_idx != -1:
                            corrected_sql = corrected_sql[next_newline:end_idx].strip()
            return corrected_sql
    except Exception as exc:  # noqa: BLE001
        logger.warning("Self-correction request failed: %s", exc)
    return None


async def execute_query(sql: str, reasoning: str = "") -> dict:
    """Tool entrypoint: Validates, bounds, and executes a read-only SQL SELECT query.

    Layers of Defense:
    1. SQLGlot AST validation (SELECT only, no DDL/writes, no locking, no dangerous functions)
    2. Automatic LIMIT clamping (max 100 rows)
    3. PostgreSQL statement timeout
    4. Dedicated restricted read-only role (agent_readonly)
    5. Sanitized error handling
    """
    start_time = time.perf_counter()
    logger.info("execute_query called with reasoning: %s", reasoning or "none")

    async def run_sql(query_str: str):
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Set session-level statement timeout as additional safeguard
            await conn.execute(f"SET statement_timeout = {int(settings.query_timeout_seconds * 1000)};")
            return await asyncio.wait_for(
                conn.fetch(query_str), timeout=settings.query_timeout_seconds
            )

    self_corrected = False
    original_sql = sql

    # --- PHASE 1: AST VALIDATION OF INITIAL QUERY ---
    try:
        stmt = _validate_select_only(sql)
        logger.info("SQL AST validation: PASS")
    except UnsafeQueryError as exc:
        original_error = str(exc)
        logger.warning("SQL AST validation: BLOCKED (%s)", original_error)

        # Only attempt self-correction for pure syntax parse errors, never for intentional write attacks!
        if "Could not parse SQL" in original_error:
            corrected_sql = await _attempt_self_correction(sql, original_error)
            if corrected_sql:
                try:
                    # STRICT: Corrected SQL must pass the exact same AST validation!
                    stmt = _validate_select_only(corrected_sql)
                    sql = corrected_sql
                    self_corrected = True
                    logger.info("Self-correction succeeded: corrected query validated.")
                except UnsafeQueryError as sec_exc:
                    logger.warning("Self-corrected SQL rejected by security validator: %s", sec_exc)
                    return {
                        "success": False,
                        "error_type": "unsafe_query",
                        "message": f"Query blocked by security validator: {sec_exc}",
                    }
            else:
                return {
                    "success": False,
                    "error_type": "syntax_error",
                    "message": "The SQL query syntax could not be parsed. Please rephrase.",
                }
        else:
            return {
                "success": False,
                "error_type": "unsafe_query",
                "message": f"Security Policy Violation: {original_error}",
            }

    # Apply row limit (default 100)
    safe_sql = _apply_row_limit(stmt, settings.query_row_limit)

    # --- PHASE 2: DATABASE EXECUTION ---
    try:
        rows = await run_sql(safe_sql)
    except asyncio.TimeoutError:
        logger.warning("Query timed out after %ss", settings.query_timeout_seconds)
        return {
            "success": False,
            "error_type": "timeout",
            "message": (
                f"Query exceeded the {settings.query_timeout_seconds}s execution timeout. "
                "Try narrowing date ranges or using aggregates."
            ),
        }
    except (
        asyncpg.exceptions.UndefinedColumnError,
        asyncpg.exceptions.UndefinedTableError,
        asyncpg.exceptions.PostgresSyntaxError,
    ) as exc:
        original_error = str(exc)
        logger.warning("Database execution error: %s. Attempting self-correction.", original_error)

        corrected_sql = await _attempt_self_correction(safe_sql, original_error)
        if corrected_sql:
            try:
                # STRICT: Every corrected query MUST pass through the security pipeline
                corrected_stmt = _validate_select_only(corrected_sql)
                corrected_safe_sql = _apply_row_limit(corrected_stmt, settings.query_row_limit)
                rows = await run_sql(corrected_safe_sql)
                safe_sql = corrected_safe_sql
                self_corrected = True
                logger.info("Self-correction successful; re-executed query safely.")
            except UnsafeQueryError as sec_exc:
                logger.warning("Self-corrected SQL blocked by security validator: %s", sec_exc)
                return {
                    "success": False,
                    "error_type": "unsafe_query",
                    "message": f"Self-corrected query blocked: {sec_exc}",
                }
            except Exception as retry_exc:
                logger.warning("Self-corrected SQL failed execution: %s", retry_exc)
                sanitized_msg = _sanitize_db_error(exc)
                return {"success": False, "error_type": "query_failed", "message": sanitized_msg}
        else:
            sanitized_msg = _sanitize_db_error(exc)
            return {"success": False, "error_type": "query_failed", "message": sanitized_msg}
    except asyncpg.exceptions.InsufficientPrivilegeError as exc:
        logger.error("DB Engine Role Permission Denied: %s", exc)
        return {
            "success": False,
            "error_type": "permission_denied",
            "message": "Database permission denied: Write operations and schema modifications are physically forbidden.",
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected query execution error: %s", exc, exc_info=True)
        return {
            "success": False,
            "error_type": "query_failed",
            "message": "The query could not be executed due to a database error.",
        }

    duration_ms = (time.perf_counter() - start_time) * 1000
    # Enforce row limit in python as well
    limited_rows = rows[:settings.query_row_limit]
    columns = list(limited_rows[0].keys()) if limited_rows else []
    result_rows = [{k: _jsonable(v) for k, v in dict(r).items()} for r in limited_rows]

    logger.info(
        "Query completed in %.1fms. Returned %d rows (truncated=%s, self_corrected=%s)",
        duration_ms,
        len(result_rows),
        len(rows) > settings.query_row_limit,
        self_corrected,
    )

    return {
        "success": True,
        "sql_executed": safe_sql,
        "columns": columns,
        "rows": result_rows,
        "row_count": len(result_rows),
        "truncated": len(rows) > settings.query_row_limit,
        "self_corrected": self_corrected,
        "original_sql": original_sql,
        "execution_time_ms": round(duration_ms, 2),
    }


def _sanitize_db_error(exc: Exception) -> str:
    """Translate technical database errors into clear, safe user-facing messages."""
    if isinstance(exc, asyncpg.exceptions.UndefinedTableError):
        return "The requested table does not exist in the database. Refer to the Schema Explorer."
    if isinstance(exc, asyncpg.exceptions.UndefinedColumnError):
        return "A requested column does not exist on this table. Refer to the Schema Explorer."
    if isinstance(exc, asyncpg.exceptions.PostgresSyntaxError):
        return "The SQL syntax was invalid for PostgreSQL."
    return "The database query failed to execute."


# Alias for backwards compatibility
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
